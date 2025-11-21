"""Query and display statistics about the crawled data."""
import os
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env or env file
load_dotenv('.env') or load_dotenv('env')


def get_connection_string() -> str:
    """Build PostgreSQL connection string from environment variables."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "github_crawler")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    
    return f"host={host} port={port} dbname={database} user={user} password={password}"


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def display_statistics():
    """Display various statistics about the crawled data."""
    conn_string = get_connection_string()
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    
    # Total count
    print_section("Overall Statistics")
    cursor.execute("SELECT COUNT(*) FROM repositories")
    total = cursor.fetchone()[0]
    print(f"Total repositories: {total:,}")
    
    # Star statistics
    cursor.execute("""
        SELECT 
            MIN(star_count) as min_stars,
            MAX(star_count) as max_stars,
            AVG(star_count)::int as avg_stars,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY star_count)::int as median_stars
        FROM repositories
    """)
    stats = cursor.fetchone()
    print(f"Star count range: {stats[0]:,} - {stats[1]:,}")
    print(f"Average stars: {stats[2]:,}")
    print(f"Median stars: {stats[3]:,}")
    
    # Top repositories
    print_section("Top 10 Repositories by Stars")
    cursor.execute("""
        SELECT full_name, star_count
        FROM repositories
        ORDER BY star_count DESC
        LIMIT 10
    """)
    
    print(f"{'Repository':<40} {'Stars':>15}")
    print("-" * 60)
    for row in cursor:
        print(f"{row[0]:<40} {row[1]:>15,}")
    
    # Repositories by star ranges
    print_section("Distribution by Star Count")
    cursor.execute("""
        SELECT 
            CASE 
                WHEN star_count < 10 THEN '1-9'
                WHEN star_count < 100 THEN '10-99'
                WHEN star_count < 1000 THEN '100-999'
                WHEN star_count < 10000 THEN '1K-9.9K'
                WHEN star_count < 100000 THEN '10K-99.9K'
                ELSE '100K+'
            END as star_range,
            COUNT(*) as count
        FROM repositories
        GROUP BY star_range
        ORDER BY MIN(star_count)
    """)
    
    print(f"{'Star Range':<20} {'Count':>15} {'Percentage':>15}")
    print("-" * 60)
    for row in cursor:
        percentage = (row[1] / total * 100) if total > 0 else 0
        print(f"{row[0]:<20} {row[1]:>15,} {percentage:>14.1f}%")
    
    # Most common owners
    print_section("Top 10 Most Prolific Owners")
    cursor.execute("""
        SELECT owner, COUNT(*) as repo_count, SUM(star_count) as total_stars
        FROM repositories
        GROUP BY owner
        ORDER BY repo_count DESC
        LIMIT 10
    """)
    
    print(f"{'Owner':<30} {'Repos':>10} {'Total Stars':>15}")
    print("-" * 60)
    for row in cursor:
        print(f"{row[0]:<30} {row[1]:>10,} {row[2]:>15,}")
    
    # Crawl times
    print_section("Crawl Information")
    cursor.execute("""
        SELECT 
            MIN(crawled_at) as first_crawl,
            MAX(crawled_at) as last_crawl,
            COUNT(DISTINCT DATE(crawled_at)) as crawl_days
        FROM repositories
    """)
    crawl_info = cursor.fetchone()
    if crawl_info[0]:
        print(f"First crawl: {crawl_info[0]}")
        print(f"Last crawl: {crawl_info[1]}")
        print(f"Number of crawl days: {crawl_info[2]}")
    
    # Recently updated
    print_section("Recently Crawled Repositories (Last 10)")
    cursor.execute("""
        SELECT full_name, star_count, crawled_at
        FROM repositories
        ORDER BY crawled_at DESC
        LIMIT 10
    """)
    
    print(f"{'Repository':<40} {'Stars':>10} {'Crawled At':<20}")
    print("-" * 80)
    for row in cursor:
        print(f"{row[0]:<40} {row[1]:>10,} {row[2]}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("Query completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        display_statistics()
    except Exception as e:
        print(f"Error: {e}")
        import sys
        sys.exit(1)

