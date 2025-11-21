"""Crawler service orchestrating the GitHub crawling operation."""
import asyncio
import logging
import time
from typing import List
from src.domain.github_interface import IGitHubClient
from src.domain.repository_interface import IRepositoryStorage
from src.domain.models import Repository, CrawlMetrics


logger = logging.getLogger(__name__)


class CrawlerService:
    """Application service for crawling GitHub repositories.
    
    Orchestrates the interaction between GitHub API and database storage.
    Follows single responsibility principle - only coordinates the crawl operation.
    """
    
    def __init__(
        self,
        github_client: IGitHubClient,
        storage: IRepositoryStorage,
        batch_size: int = 1000
    ):
        """Initialize crawler service.
        
        Args:
            github_client: GitHub API client implementation
            storage: Repository storage implementation
            batch_size: Number of repositories to batch before saving
        """
        self._github_client = github_client
        self._storage = storage
        self._batch_size = batch_size
    
    async def crawl_repositories(self, count: int) -> CrawlMetrics:
        """Crawl GitHub repositories and store them.
        
        Fetches repositories in batches and saves them to storage efficiently.
        
        Args:
            count: Number of repositories to crawl
            
        Returns:
            CrawlMetrics with operation statistics
        """
        start_time = time.time()
        repositories_crawled = 0
        errors = 0
        rate_limit_resets = 0
        
        logger.info(f"Starting crawl for {count} repositories")
        
        try:
            batch: List[Repository] = []
            
            async for repository in self._github_client.fetch_repositories(count):
                batch.append(repository)
                
                # Save in batches for efficiency
                if len(batch) >= self._batch_size:
                    try:
                        self._storage.save_repositories(batch)
                        repositories_crawled += len(batch)
                        logger.info(
                            f"Saved batch of {len(batch)} repositories. "
                            f"Total: {repositories_crawled}/{count}"
                        )
                        batch = []
                    except Exception as e:
                        logger.error(f"Error saving batch: {e}")
                        errors += 1
                        # Don't fail entire operation for one batch error
            
            # Save remaining repositories
            if batch:
                try:
                    self._storage.save_repositories(batch)
                    repositories_crawled += len(batch)
                    logger.info(f"Saved final batch of {len(batch)} repositories")
                except Exception as e:
                    logger.error(f"Error saving final batch: {e}")
                    errors += 1
            
        except Exception as e:
            logger.error(f"Error during crawl: {e}")
            errors += 1
            raise
        
        duration = time.time() - start_time
        
        metrics = CrawlMetrics(
            repositories_crawled=repositories_crawled,
            duration_seconds=duration,
            rate_limit_resets=rate_limit_resets,
            errors_encountered=errors
        )
        
        logger.info(
            f"Crawl completed: {repositories_crawled} repositories in "
            f"{duration:.2f} seconds ({repositories_crawled/duration:.2f} repos/sec)"
        )
        
        return metrics
    
    async def close(self) -> None:
        """Close connections."""
        await self._github_client.close()
        self._storage.close()

