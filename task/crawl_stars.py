"""Main entry point for the GitHub crawler.

This script orchestrates the crawling operation using the application service.
"""
import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
from src.infrastructure.github_client import GitHubGraphQLClient
from src.infrastructure.postgres_repository import PostgresRepositoryStorage
from src.application.crawler_service import CrawlerService

# Load environment variables from .env or env file
load_dotenv('.env') or load_dotenv('env')


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_connection_string() -> str:
    """Build PostgreSQL connection string from environment variables."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "github_crawler")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    
    return f"host={host} port={port} dbname={database} user={user} password={password}"


async def main():
    """Execute the crawling operation."""
    # Get configuration from environment
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable is required")
        sys.exit(1)
    
    target_count = int(os.getenv("TARGET_REPO_COUNT", "100000"))
    batch_size = int(os.getenv("BATCH_SIZE", "1000"))
    
    logger.info(f"Starting GitHub crawler for {target_count} repositories")
    
    # Initialize infrastructure components
    conn_string = get_connection_string()
    storage = PostgresRepositoryStorage(conn_string)
    github_client = GitHubGraphQLClient(github_token, batch_size=100)
    
    # Initialize application service
    crawler = CrawlerService(
        github_client=github_client,
        storage=storage,
        batch_size=batch_size
    )
    
    try:
        # Execute crawl
        metrics = await crawler.crawl_repositories(target_count)
        
        # Log results
        logger.info("=" * 50)
        logger.info("Crawl Metrics:")
        logger.info(f"  Repositories crawled: {metrics.repositories_crawled}")
        logger.info(f"  Duration: {metrics.duration_seconds:.2f} seconds")
        logger.info(f"  Rate: {metrics.repositories_crawled / metrics.duration_seconds:.2f} repos/sec")
        logger.info(f"  Errors: {metrics.errors_encountered}")
        logger.info("=" * 50)
        
        # Verify storage
        stored_count = storage.get_repository_count()
        logger.info(f"Total repositories in database: {stored_count}")
        
    except Exception as e:
        logger.error(f"Crawl failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())

