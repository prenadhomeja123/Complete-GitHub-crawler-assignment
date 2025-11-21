"""PostgreSQL repository implementation for data persistence."""
import logging
from typing import List
import psycopg2
from psycopg2.extras import execute_values
from src.domain.repository_interface import IRepositoryStorage
from src.domain.models import Repository


logger = logging.getLogger(__name__)


class PostgresRepositoryStorage(IRepositoryStorage):
    """PostgreSQL implementation of repository storage.
    
    Uses efficient UPSERT operations for updating existing records.
    The schema is designed to be flexible and support future extensions.
    """
    
    def __init__(self, connection_string: str):
        """Initialize PostgreSQL connection.
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self._connection_string = connection_string
        self._conn = psycopg2.connect(connection_string)
        self._conn.autocommit = False
        logger.info("Connected to PostgreSQL database")
    
    def save_repositories(self, repositories: List[Repository]) -> None:
        """Save or update repositories using efficient UPSERT.
        
        Uses PostgreSQL's ON CONFLICT clause for efficient upserts.
        This ensures minimal rows are affected when updating existing records.
        
        Args:
            repositories: List of Repository entities to persist
        """
        if not repositories:
            return
        
        cursor = self._conn.cursor()
        
        try:
            # Prepare data for bulk insert
            values = [
                (
                    repo.owner,
                    repo.name,
                    repo.full_name,
                    repo.star_count,
                    repo.crawled_at
                )
                for repo in repositories
            ]
            
            # Use ON CONFLICT for efficient upsert
            # Only updates the row if star_count or crawled_at changed
            query = """
                INSERT INTO repositories (owner, name, full_name, star_count, crawled_at, updated_at)
                VALUES %s
                ON CONFLICT (owner, name)
                DO UPDATE SET
                    star_count = EXCLUDED.star_count,
                    crawled_at = EXCLUDED.crawled_at,
                    updated_at = CURRENT_TIMESTAMP
                WHERE repositories.star_count != EXCLUDED.star_count
                   OR repositories.crawled_at < EXCLUDED.crawled_at
            """
            
            execute_values(
                cursor,
                query,
                values,
                template="(%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)"
            )
            
            self._conn.commit()
            logger.info(f"Saved {len(repositories)} repositories to database")
            
        except Exception as e:
            self._conn.rollback()
            logger.error(f"Error saving repositories: {e}")
            raise
        finally:
            cursor.close()
    
    def get_repository_count(self) -> int:
        """Get the total number of repositories in storage.
        
        Returns:
            Count of repositories
        """
        cursor = self._conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM repositories")
            count = cursor.fetchone()[0]
            return count
        finally:
            cursor.close()
    
    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            logger.info("Closed PostgreSQL connection")

