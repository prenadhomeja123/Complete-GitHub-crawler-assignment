# Quick Start Guide

Get the GitHub crawler up and running in 5 minutes.

## Prerequisites

- Python 3.11+
- PostgreSQL 16+ (or Docker)
- GitHub account (for API token)

## Step 1: Get GitHub Token

The default GitHub Actions token (`GITHUB_TOKEN`) works automatically in CI/CD.

For local development:

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `public_repo`, `read:org`
4. Generate and copy the token

## Step 2: Start PostgreSQL

**Option A: Using Docker** (recommended):

```bash
docker run -d \
  --name github-crawler-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=github_crawler \
  -p 5432:5432 \
  postgres:16
```

**Option B: Local PostgreSQL**:

Install PostgreSQL and create a database named `github_crawler`.

## Step 3: Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/github-crawler.git
cd github-crawler

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 4: Configure Environment

```bash
# Copy example environment file
cp env.example .env

# Edit .env with your settings
# Minimum required: GITHUB_TOKEN=your_token_here
```

**Example `.env` file**:

```env
GITHUB_TOKEN=ghp_your_token_here
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=github_crawler
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
TARGET_REPO_COUNT=1000
BATCH_SIZE=1000
```

## Step 5: Initialize Database

```bash
python setup_postgres.py
```

Expected output:
```
INFO - Connecting to database...
INFO - Database schema created successfully
INFO - Database initialization completed successfully
```

## Step 6: Run Crawler

**Small test run** (10 repositories):

```bash
export TARGET_REPO_COUNT=10
python crawl_stars.py
```

**Full run** (100,000 repositories):

```bash
export TARGET_REPO_COUNT=100000
python crawl_stars.py
```

Expected output:
```
INFO - Starting GitHub crawler for 10 repositories
INFO - Fetched 10/10 repositories
INFO - Saved batch of 10 repositories. Total: 10/10
==================================================
Crawl Metrics:
  Repositories crawled: 10
  Duration: 5.23 seconds
  Rate: 1.91 repos/sec
  Errors: 0
==================================================
INFO - Total repositories in database: 10
```

## Step 7: Export Results

```bash
python export_database.py repositories.csv
```

This creates a CSV file with all crawled repositories:

```csv
id,owner,name,full_name,star_count,crawled_at,created_at,updated_at
1,facebook,react,facebook/react,200000,2024-01-15 10:30:00,...
2,microsoft,vscode,microsoft/vscode,150000,2024-01-15 10:30:01,...
```

## Step 8: View Results

**Option A: PostgreSQL CLI**:

```bash
psql -h localhost -U postgres -d github_crawler

github_crawler=# SELECT owner, name, star_count FROM repositories ORDER BY star_count DESC LIMIT 10;
```

**Option B: View CSV**:

```bash
head -20 repositories.csv
```

## Using with GitHub Actions

The workflow is already configured. Just:

1. Push to GitHub
2. Go to **Actions** tab
3. Click **GitHub Repository Crawler**
4. Click **Run workflow**
5. Download the artifact when complete

The workflow uses the default `GITHUB_TOKEN` automatically - no secrets needed!

## Common Issues

### "psycopg2.OperationalError: could not connect to server"

**Solution**: Ensure PostgreSQL is running:

```bash
# Check if container is running
docker ps

# Start if not running
docker start github-crawler-db
```

### "Authentication required" / "Bad credentials"

**Solution**: Check your GitHub token:

```bash
# Verify token is set
echo $GITHUB_TOKEN

# Test token
curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user
```

### Rate limit errors

**Solution**: 
- Standard token: 5,000 requests/hour
- The crawler automatically waits when rate limit is low
- For faster crawling, use multiple tokens or GitHub App

### "Table repositories does not exist"

**Solution**: Run database initialization:

```bash
python setup_postgres.py
```

## Next Steps

- **Read the architecture**: See `ARCHITECTURE.md` for design details
- **Scaling considerations**: See `SCALING.md` for 500M repo strategy  
- **Contributing**: See `CONTRIBUTING.md` for development guidelines
- **Full documentation**: See `README.md`

## Performance Tips

1. **Increase batch size** for faster saves:
   ```bash
   export BATCH_SIZE=5000
   ```

2. **Use multiple workers** (future enhancement):
   - Deploy multiple crawler instances
   - Each crawls different segments

3. **Monitor rate limits**:
   - Check logs for "Rate limit remaining" messages
   - Crawler automatically handles rate limits

4. **Database optimization**:
   - Keep PostgreSQL updated
   - Regular VACUUM and ANALYZE
   - Monitor disk space

## Quick Reference

```bash
# Install
make install

# Setup database
make setup-db

# Run crawler
make crawl

# Export results
make export

# Run tests
make test

# Clean
make clean
```

## Verification

After running, verify everything works:

```bash
# Check repository count
python -c "
import psycopg2
conn = psycopg2.connect('host=localhost dbname=github_crawler user=postgres password=postgres')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM repositories')
print(f'Total repositories: {cur.fetchone()[0]}')
conn.close()
"
```

## Support

- Open an issue on GitHub
- Check existing documentation
- Review example runs in Actions tab

Happy crawling! 🚀

