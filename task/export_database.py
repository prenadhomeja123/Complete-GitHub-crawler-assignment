"""Export database contents to CSV for GitHub Actions artifact."""
import os
import sys
import csv
import logging
import psycopg2
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


def export_to_csv(output_file: str = "repositories.csv"):
    """Export repositories table to CSV file.
    
    Args:
        output_file: Path to output CSV file
    """
    conn_string = get_connection_string()
    
    try:
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        
        # Query all repositories
        cursor.execute("""
            SELECT id, owner, name, full_name, star_count, crawled_at, created_at, updated_at
            FROM repositories
            ORDER BY star_count DESC
        """)
        
        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'id', 'owner', 'name', 'full_name', 'star_count',
                'crawled_at', 'created_at', 'updated_at'
            ])
            
            # Write data
            row_count = 0
            for row in cursor:
                writer.writerow(row)
                row_count += 1
        
        logger.info(f"Exported {row_count} repositories to {output_file}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error exporting database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    output_file = sys.argv[1] if len(sys.argv) > 1 else "repositories.csv"
    export_to_csv(output_file)

