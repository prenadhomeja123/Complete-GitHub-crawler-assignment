"""Database initialization script.

Creates the schema with tables optimized for efficient updates and future extensibility.
"""
import os
import sys
import psycopg2
import logging
from dotenv import load_dotenv

# Load environment variables from .env or env file
load_dotenv('.env') or load_dotenv('env')


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_connection_string() -> str:
    """Build PostgreSQL connection string from environment variables."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "github_crawler")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    
    return f"host={host} port={port} dbname={database} user={user} password={password}"


def create_schema(conn) -> None:
    """Create database schema.
    
    Schema design considerations:
    - repositories table is the core, with owner+name as natural composite key
    - Indexed on commonly queried fields (star_count, crawled_at)
    - created_at tracks when first seen, updated_at tracks last modification
    - Full name stored for convenience but derived from owner+name
    - Schema is designed to be extended with additional metadata tables
    
    Future extensibility:
    - issues table: repo_id FK, issue_number unique per repo
    - pull_requests table: repo_id FK, pr_number unique per repo
    - comments table: polymorphic association to issues/PRs
    - commits table: repo_id FK, sha unique
    - reviews table: pr_id FK
    - ci_checks table: commit_id FK
    
    All future tables will reference repositories(id) as foreign key.
    Updates to child tables (e.g., new comments on PR) only affect those tables,
    not the parent repository record.
    """
    cursor = conn.cursor()
    
    try:
        # Main repositories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id SERIAL PRIMARY KEY,
                owner VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                full_name VARCHAR(511) NOT NULL,
                star_count INTEGER NOT NULL DEFAULT 0,
                crawled_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT repositories_owner_name_unique UNIQUE (owner, name)
            )
        """)
        
        # Index for efficient queries by star count
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_repositories_star_count 
            ON repositories(star_count DESC)
        """)
        
        # Index for queries by crawl time (useful for incremental updates)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_repositories_crawled_at 
            ON repositories(crawled_at DESC)
        """)
        
        # Index on full_name for lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_repositories_full_name 
            ON repositories(full_name)
        """)
        
        # Example future extension: issues table (not created yet, just documented)
        # This shows how schema can be extended efficiently
        """
        CREATE TABLE IF NOT EXISTS issues (
            id SERIAL PRIMARY KEY,
            repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
            issue_number INTEGER NOT NULL,
            title TEXT NOT NULL,
            state VARCHAR(50) NOT NULL,
            comment_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT issues_repo_number_unique UNIQUE (repository_id, issue_number)
        );
        
        CREATE INDEX idx_issues_repository_id ON issues(repository_id);
        CREATE INDEX idx_issues_updated_at ON issues(updated_at DESC);
        """
        
        conn.commit()
        logger.info("Database schema created successfully")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating schema: {e}")
        raise
    finally:
        cursor.close()


def main():
    """Initialize the database."""
    try:
        conn_string = get_connection_string()
        logger.info(f"Connecting to database...")
        
        conn = psycopg2.connect(conn_string)
        conn.autocommit = False
        
        create_schema(conn)
        
        conn.close()
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

