# GitHub Repository Crawler

A production-ready GitHub repository crawler that fetches star counts for 100,000+ repositories using GitHub's GraphQL API and stores them in PostgreSQL. Built with clean architecture principles, emphasizing immutability, separation of concerns, and efficient data operations.

## Features

- **Clean Architecture**: Clear separation between domain, application, and infrastructure layers
- **Anti-Corruption Layer**: Domain models isolated from external API specifics
- **Rate Limiting**: Intelligent handling of GitHub API rate limits with automatic retry
- **Efficient Storage**: PostgreSQL with optimized UPSERT operations for minimal row impact
- **Extensible Schema**: Designed to support future metadata (issues, PRs, commits, etc.)
- **Immutable Domain Models**: Using frozen dataclasses for thread-safety
- **GitHub Actions Integration**: Fully automated CI/CD pipeline

## Architecture

### Clean Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│              (crawler_service.py - Use Cases)            │
├─────────────────────────────────────────────────────────┤
│                     Domain Layer                         │
│  (models.py - Entities, Interfaces - Ports)             │
├─────────────────────────────────────────────────────────┤
│                  Infrastructure Layer                    │
│  (github_client.py, postgres_repository.py - Adapters)  │
└─────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Dependency Inversion**: Domain defines interfaces (`IGitHubClient`, `IRepositoryStorage`), infrastructure implements them
2. **Single Responsibility**: Each module has one clear purpose
3. **Immutability**: Domain entities are immutable (frozen dataclasses)
4. **Anti-Corruption Layer**: GitHub API specifics don't leak into domain logic
5. **Separation of Concerns**: Business logic independent of frameworks and external services

## Database Schema

### Current Schema

```sql
CREATE TABLE repositories (
    id SERIAL PRIMARY KEY,
    owner VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    full_name VARCHAR(511) NOT NULL,
    star_count INTEGER NOT NULL DEFAULT 0,
    crawled_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT repositories_owner_name_unique UNIQUE (owner, name)
);

CREATE INDEX idx_repositories_star_count ON repositories(star_count DESC);
CREATE INDEX idx_repositories_crawled_at ON repositories(crawled_at DESC);
CREATE INDEX idx_repositories_full_name ON repositories(full_name);
```

### Schema Design Rationale

- **Natural Key**: `(owner, name)` composite unique constraint prevents duplicates
- **Efficient Updates**: UPSERT using `ON CONFLICT` only updates when data actually changes
- **Temporal Tracking**: `created_at` (first seen) and `updated_at` (last modified) separated from `crawled_at` (last checked)
- **Indexes**: Optimized for common queries (by star count, by crawl time, by name)

### Future Extensibility

The schema is designed to accommodate additional metadata efficiently:

```sql
-- Issues table (example extension)
CREATE TABLE issues (
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

-- Pull requests table (example extension)
CREATE TABLE pull_requests (
    id SERIAL PRIMARY KEY,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    pr_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    state VARCHAR(50) NOT NULL,
    comment_count INTEGER NOT NULL DEFAULT 0,
    commit_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pr_repo_number_unique UNIQUE (repository_id, pr_number)
);

-- Comments table (polymorphic for issues and PRs)
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER REFERENCES issues(id) ON DELETE CASCADE,
    pull_request_id INTEGER REFERENCES pull_requests(id) ON DELETE CASCADE,
    author VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT comment_parent_check CHECK (
        (issue_id IS NOT NULL AND pull_request_id IS NULL) OR
        (issue_id IS NULL AND pull_request_id IS NOT NULL)
    )
);

-- Similar tables for: commits, reviews, ci_checks, etc.
```

**Efficient Update Pattern**: When a PR gets 10 new comments, only 10 rows are inserted into the `comments` table. The PR record's `comment_count` is updated (1 row), but the repository record is unaffected. This minimizes write amplification.

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- GitHub Personal Access Token (or use GitHub Actions token)

### Local Development

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/github-crawler.git
cd github-crawler
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up PostgreSQL**:
```bash
# Start PostgreSQL (example using Docker)
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=github_crawler \
  -p 5432:5432 \
  postgres:16

# Create schema
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=github_crawler
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
python setup_postgres.py
```

4. **Run the crawler**:
```bash
export GITHUB_TOKEN=your_github_token
export TARGET_REPO_COUNT=100000
python crawl_stars.py
```

5. **Export results**:
```bash
python export_database.py repositories.csv
```

## GitHub Actions

The workflow (`.github/workflows/crawl.yml`) automatically:

1. ✅ Spins up a PostgreSQL service container
2. ✅ Installs Python dependencies
3. ✅ Creates database schema
4. ✅ Crawls 100,000 repositories using the default `GITHUB_TOKEN`
5. ✅ Exports results to CSV
6. ✅ Uploads CSV as a workflow artifact

**To trigger manually**: Go to Actions tab → GitHub Repository Crawler → Run workflow

## Performance Characteristics

### Current Scale (100,000 repos)

- **Fetch Rate**: ~50-100 repos/second (limited by GitHub API rate limits)
- **Expected Duration**: ~15-30 minutes for 100,000 repos
- **Rate Limit**: 5,000 requests/hour with GitHub token
- **Batch Processing**: Saves in batches of 1,000 to minimize database round-trips

### Rate Limit Handling

- Monitors rate limit remaining after each API call
- Automatically waits when rate limit is nearly exhausted
- Exponential backoff retry for transient failures
- Respects GitHub's rate limit reset time

## Scaling to 500 Million Repositories

### Changes Required for 500M Scale

1. **Distributed Crawling**:
   - Deploy multiple crawler instances with different search queries to parallelize
   - Use message queue (RabbitMQ/SQS) to distribute work across workers
   - Partition by language, star count ranges, or creation date
   - Each worker crawls a specific segment

2. **Database Scaling**:
   - Implement PostgreSQL partitioning by date or owner hash
   - Use read replicas for query workloads
   - Consider time-series database (TimescaleDB) for temporal data
   - Implement connection pooling (PgBouncer)
   - Archive old snapshots to cold storage (S3)

3. **Rate Limit Management**:
   - Use multiple GitHub tokens rotating across workers
   - Implement centralized rate limit coordination (Redis)
   - Consider GitHub Apps for higher rate limits (5,000 → 15,000/hour)

4. **Storage Optimization**:
   - Incremental updates: only fetch changed repos
   - Store deltas instead of full snapshots
   - Compress archived data
   - Use columnar storage (Parquet) for analytics

5. **Infrastructure**:
   - Kubernetes for orchestrating crawler pods
   - Auto-scaling based on queue depth
   - Monitoring and alerting (Prometheus/Grafana)
   - Dead letter queue for failed items

6. **Performance Optimizations**:
   - Increase batch sizes to 10,000+
   - Use PostgreSQL COPY for bulk inserts
   - Async I/O throughout the pipeline
   - Cache frequently accessed metadata in Redis

7. **Reliability**:
   - Idempotent operations (resume from failure)
   - Checkpoint progress to resume interrupted crawls
   - Circuit breakers for failing API calls
   - Health checks and automatic recovery

### Estimated Resources for 500M Scale

- **Crawl Time**: ~7-10 days with 10 workers (with rate limits)
- **Storage**: ~500GB for core data, ~5TB with full metadata
- **Database**: 4-8 vCPUs, 16-32GB RAM, 1TB SSD
- **Workers**: 10+ crawler instances, 2 vCPUs each
- **Cost**: ~$500-1000/month on cloud providers

## Schema Evolution Strategy

### Adding New Metadata

When adding new metadata types (issues, PRs, commits, comments, reviews, CI checks):

1. **Create Related Tables**: Each metadata type gets its own table with `repository_id` foreign key
2. **Use Natural Unique Constraints**: e.g., `(repository_id, issue_number)` for issues
3. **Store Counts in Parent**: Keep counts in parent table for quick access without joins
4. **Efficient Updates**: Only insert/update changed records
5. **Temporal Consistency**: Track `created_at` and `updated_at` separately

### Example: Adding Issue Comments

```python
# When an issue gets 10 new comments (from 10 → 30 total):

# 1. Insert 10 new rows in comments table (10 rows affected)
INSERT INTO comments (issue_id, author, body, created_at) VALUES ...

# 2. Update issue comment count (1 row affected)
UPDATE issues SET comment_count = 30, updated_at = NOW() WHERE id = ?

# 3. Repository and pull_requests tables: 0 rows affected
# Total: 11 rows affected (minimal impact)
```

### Migration Strategy

```sql
-- Step 1: Add new table (zero downtime)
CREATE TABLE new_metadata (...);

-- Step 2: Backfill historical data (background job)
INSERT INTO new_metadata SELECT ...;

-- Step 3: Update application code to write to new table

-- Step 4: Add constraints after backfill complete
ALTER TABLE new_metadata ADD CONSTRAINT ...;
```

## Testing

```bash
# Run tests (when implemented)
pytest tests/

# Type checking
mypy src/

# Code formatting
black src/
```

## Project Structure

```
github-crawler/
├── .github/
│   └── workflows/
│       └── crawl.yml          # GitHub Actions workflow
├── src/
│   ├── domain/                # Domain layer (core business logic)
│   │   ├── models.py          # Immutable entities
│   │   ├── github_interface.py    # GitHub API port
│   │   └── repository_interface.py # Storage port
│   ├── application/           # Application layer (use cases)
│   │   └── crawler_service.py # Crawl orchestration
│   └── infrastructure/        # Infrastructure layer (adapters)
│       ├── github_client.py   # GitHub GraphQL implementation
│       └── postgres_repository.py # PostgreSQL implementation
├── setup_postgres.py          # Database initialization
├── crawl_stars.py            # Main entry point
├── export_database.py        # Export to CSV
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## License

MIT

## Contributing

Contributions welcome! Please ensure:
- Clean architecture principles are maintained
- Domain logic remains independent of frameworks
- Tests are included for new features
- Code follows existing style (immutability, type hints, etc.)

