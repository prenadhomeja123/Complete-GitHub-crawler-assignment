"""GitHub GraphQL API client implementation with rate limiting and retry logic."""
import asyncio
import logging
from datetime import datetime
from typing import AsyncIterator, Optional
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from src.domain.github_interface import IGitHubClient
from src.domain.models import Repository


logger = logging.getLogger(__name__)


class RateLimitException(Exception):
    """Exception raised when rate limit is hit."""
    pass


class GitHubGraphQLClient(IGitHubClient):
    """GitHub GraphQL API client with rate limiting and retry mechanisms.
    
    Implements the IGitHubClient port, providing an anti-corruption layer
    between the domain and GitHub's API.
    """
    
    # GraphQL query to fetch repositories with star counts
    REPOSITORY_QUERY = gql("""
        query SearchRepositories($cursor: String) {
            search(
                query: "stars:>1"
                type: REPOSITORY
                first: 100
                after: $cursor
            ) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    ... on Repository {
                        owner {
                            login
                        }
                        name
                        stargazerCount
                    }
                }
            }
            rateLimit {
                remaining
                resetAt
            }
        }
    """)
    
    def __init__(self, access_token: str, batch_size: int = 100):
        """Initialize GitHub client.
        
        Args:
            access_token: GitHub personal access token
            batch_size: Number of repositories to fetch per request (max 100)
        """
        self._access_token = access_token
        self._batch_size = min(batch_size, 100)  # GitHub max is 100
        self._transport: Optional[AIOHTTPTransport] = None
        self._client: Optional[Client] = None
        self._rate_limit_remaining: int = 5000
        self._rate_limit_reset_at: Optional[datetime] = None
    
    async def _init_client(self) -> None:
        """Initialize the GraphQL client (lazy initialization)."""
        if self._client is None:
            headers = {"Authorization": f"Bearer {self._access_token}"}
            self._transport = AIOHTTPTransport(
                url="https://api.github.com/graphql",
                headers=headers
            )
            self._client = Client(
                transport=self._transport,
                fetch_schema_from_transport=False
            )
    
    async def _check_rate_limit(self) -> None:
        """Check and handle rate limiting."""
        if self._rate_limit_remaining <= 10:
            if self._rate_limit_reset_at:
                wait_time = (self._rate_limit_reset_at - datetime.now()).total_seconds()
                if wait_time > 0:
                    logger.warning(
                        f"Rate limit nearly exhausted. Waiting {wait_time:.0f} seconds "
                        f"until reset at {self._rate_limit_reset_at}"
                    )
                    await asyncio.sleep(wait_time + 1)  # Add 1 second buffer
    
    @retry(
        retry=retry_if_exception_type((RateLimitException, asyncio.TimeoutError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def _execute_query(self, cursor: Optional[str] = None) -> dict:
        """Execute GraphQL query with retry logic.
        
        Args:
            cursor: Pagination cursor for fetching next page
            
        Returns:
            Query result dictionary
            
        Raises:
            RateLimitException: When rate limit is hit
        """
        await self._init_client()
        await self._check_rate_limit()
        
        try:
            async with self._client as session:
                result = await session.execute(
                    self.REPOSITORY_QUERY,
                    variable_values={"cursor": cursor}
                )
                
                # Update rate limit info
                rate_limit = result.get("rateLimit", {})
                self._rate_limit_remaining = rate_limit.get("remaining", 0)
                reset_at_str = rate_limit.get("resetAt")
                if reset_at_str:
                    self._rate_limit_reset_at = datetime.fromisoformat(
                        reset_at_str.replace("Z", "+00:00")
                    )
                
                logger.info(
                    f"Rate limit remaining: {self._rate_limit_remaining}, "
                    f"resets at: {self._rate_limit_reset_at}"
                )
                
                return result
                
        except Exception as e:
            logger.error(f"Error executing GraphQL query: {e}")
            if "rate limit" in str(e).lower():
                raise RateLimitException(str(e))
            raise
    
    async def fetch_repositories(self, count: int) -> AsyncIterator[Repository]:
        """Fetch repositories from GitHub.
        
        Implements pagination to fetch the requested number of repositories.
        Yields repositories in batches for efficient processing.
        
        Args:
            count: Number of repositories to fetch
            
        Yields:
            Repository domain entities
        """
        fetched = 0
        cursor = None
        crawled_at = datetime.utcnow()
        
        logger.info(f"Starting to fetch {count} repositories from GitHub")
        
        while fetched < count:
            try:
                result = await self._execute_query(cursor)
                search_result = result.get("search", {})
                nodes = search_result.get("nodes", [])
                page_info = search_result.get("pageInfo", {})
                
                for node in nodes:
                    if fetched >= count:
                        break
                    
                    # Transform GitHub API response to domain entity
                    owner = node.get("owner", {}).get("login")
                    name = node.get("name")
                    star_count = node.get("stargazerCount", 0)
                    
                    if owner and name:
                        repository = Repository(
                            owner=owner,
                            name=name,
                            star_count=star_count,
                            crawled_at=crawled_at
                        )
                        yield repository
                        fetched += 1
                
                # Check if there are more pages
                if not page_info.get("hasNextPage") or fetched >= count:
                    break
                
                cursor = page_info.get("endCursor")
                logger.info(f"Fetched {fetched}/{count} repositories")
                
            except Exception as e:
                logger.error(f"Error fetching repositories: {e}")
                raise
        
        logger.info(f"Successfully fetched {fetched} repositories")
    
    async def close(self) -> None:
        """Close the GraphQL client and transport."""
        if self._transport:
            await self._transport.close()
            self._transport = None
            self._client = None

