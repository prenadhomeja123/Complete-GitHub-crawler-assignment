"""Verify that the setup is correct before running the crawler."""
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env or env file
load_dotenv('.env') or load_dotenv('env')


def check_environment_variables():
    """Check required environment variables."""
    print("Checking environment variables...")
    
    required_vars = ["GITHUB_TOKEN"]
    optional_vars = ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        return False
    
    print("✅ Required environment variables set")
    
    for var in optional_vars:
        if os.getenv(var):
            print(f"   {var}: {os.getenv(var)}")
    
    return True


def check_database_connection():
    """Check PostgreSQL connection."""
    print("\nChecking database connection...")
    
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "github_crawler")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    
    try:
        conn_string = f"host={host} port={port} dbname={database} user={user} password={password}"
        conn = psycopg2.connect(conn_string)
        conn.close()
        print(f"✅ Successfully connected to PostgreSQL at {host}:{port}")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        return False


def check_database_schema():
    """Check if database schema exists."""
    print("\nChecking database schema...")
    
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "github_crawler")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    
    try:
        conn_string = f"host={host} port={port} dbname={database} user={user} password={password}"
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'repositories'
        """)
        
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM repositories")
            count = cursor.fetchone()[0]
            print(f"✅ Database schema exists")
            print(f"   Current repository count: {count}")
            result = True
        else:
            print("❌ Database schema not found. Run 'python setup_postgres.py' first.")
            result = False
        
        cursor.close()
        conn.close()
        return result
        
    except Exception as e:
        print(f"❌ Failed to check schema: {e}")
        return False


def check_github_token():
    """Verify GitHub token is valid."""
    print("\nChecking GitHub token...")
    
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN not set")
        return False
    
    # Simple check - token format
    if token.startswith("ghp_") or token.startswith("github_pat_"):
        print("✅ GitHub token format looks valid")
        print(f"   Token prefix: {token[:10]}...")
        return True
    else:
        print("⚠️  Token format may be invalid (expected ghp_* or github_pat_*)")
        return True  # Don't fail, might be old format


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("GitHub Crawler - Setup Verification")
    print("=" * 60)
    
    checks = [
        ("Environment Variables", check_environment_variables),
        ("Database Connection", check_database_connection),
        ("Database Schema", check_database_schema),
        ("GitHub Token", check_github_token),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"❌ {name} check failed with exception: {e}")
            results[name] = False
    
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ All checks passed! Ready to run the crawler.")
        print("\nNext steps:")
        print("  python crawl_stars.py")
        sys.exit(0)
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        print("\nCommon solutions:")
        print("  - Set GITHUB_TOKEN: export GITHUB_TOKEN=your_token")
        print("  - Start PostgreSQL: docker start github-crawler-db")
        print("  - Create schema: python setup_postgres.py")
        sys.exit(1)


if __name__ == "__main__":
    main()

