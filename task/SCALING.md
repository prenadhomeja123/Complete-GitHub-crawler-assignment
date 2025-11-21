# Scaling and Schema Evolution

This document addresses specific questions about scaling to 500 million repositories and evolving the schema for additional metadata.

## Scaling from 100K to 500M Repositories

### Current Limitations at 100K Scale

1. **Single-threaded crawler**: One sequential API call stream
2. **Rate limits**: 5,000 GraphQL requests/hour with standard token
3. **Single database instance**: No horizontal scaling
4. **Synchronous processing**: One batch at a time

### Changes for 500M Repository Scale

#### 1. Distributed Architecture

**Current (100K)**:
```
GitHub API → Single Crawler → PostgreSQL
```

**500M Scale**:
```
                     ┌→ Crawler Worker 1 ┐
GitHub API → Queue → ├→ Crawler Worker 2 ├→ PostgreSQL Cluster
                     ├→ Crawler Worker 3 │  (with partitioning)
                     └→ Crawler Worker N ┘
```

**Implementation Details**:
- Use **Amazon SQS**, **RabbitMQ**, or **Redis Streams** for work distribution
- Each worker consumes a subset of repositories to crawl
- Partition work by:
  - Star count ranges (`stars:1000..2000`)
  - Languages (`language:python`)
  - Creation date ranges (`created:2020-01-01..2020-12-31`)
  - Owner name hash (A-F, G-M, N-Z)

#### 2. Rate Limit Management at Scale

**Current**: Single token, 5,000 requests/hour

**500M Scale Options**:

a) **Multiple Personal Access Tokens**:
   - Rotate 10 tokens across workers
   - 50,000 requests/hour total
   - Central Redis coordinator tracks token usage

b) **GitHub App**:
   - 15,000 requests/hour per installation
   - Better for organizational use
   - Can install on multiple organizations

c) **Enterprise Agreement**:
   - Negotiate higher limits with GitHub
   - Required for serious 500M scale operation

**Coordination Strategy**:
```python
# Pseudo-code for distributed rate limit tracking
class DistributedRateLimiter:
    def __init__(self, redis_client, tokens: List[str]):
        self.redis = redis_client
        self.tokens = tokens
    
    async def acquire_token(self) -> str:
        """Get a token with available rate limit."""
        for token in self.tokens:
            remaining = await self.redis.get(f"rate_limit:{token}")
            if int(remaining) > 100:  # Buffer
                return token
        
        # All tokens exhausted, wait for reset
        await self.wait_for_reset()
        return await self.acquire_token()
```

#### 3. Database Scaling

**Current**: Single PostgreSQL instance

**500M Scale**:

a) **Table Partitioning**:
```sql
-- Partition by date for time-series queries
CREATE TABLE repositories (
    ...
) PARTITION BY RANGE (crawled_at);

CREATE TABLE repositories_2024_01 PARTITION OF repositories
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE repositories_2024_02 PARTITION OF repositories
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- etc.

-- OR partition by hash for even distribution
CREATE TABLE repositories (
    ...
) PARTITION BY HASH (owner);

CREATE TABLE repositories_0 PARTITION OF repositories
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
-- ... create 16 partitions total
```

b) **Read Replicas**:
- 1 primary for writes
- 3-5 replicas for read queries
- Connection pooler (PgBouncer) to manage connections

c) **Sharding** (if single server insufficient):
- Shard by `owner` hash (consistent hashing)
- Shard 1: owners starting with A-G
- Shard 2: owners starting with H-N
- Shard 3: owners starting with O-Z
- Application layer routes queries to correct shard

d) **Archival Strategy**:
- Keep last 30 days in "hot" tables (fast SSD)
- Archive older data to S3/GCS in Parquet format
- Use external tables or restore on-demand for historical queries

#### 4. Incremental Updates

**Current**: Crawl all 100K repos each time

**500M Scale**: Only update what changed

```python
# Incremental crawl strategy
async def incremental_crawl(since: datetime):
    """
    Only fetch repositories updated since last crawl.
    Use GraphQL query with pushed:>YYYY-MM-DD filter.
    """
    query = """
        query($since: DateTime!, $cursor: String) {
            search(
                query: "pushed:>${since} stars:>1"
                type: REPOSITORY
                first: 100
                after: $cursor
            ) { ... }
        }
    """
    # This drastically reduces the crawl time for daily updates
```

**Benefits**:
- Full crawl once (7-10 days)
- Daily incremental updates (1-2 hours for active repos)
- Reduces load on GitHub API and database

#### 5. Storage Format Optimization

**Current**: Row-oriented PostgreSQL

**500M Scale**: Hybrid approach

a) **Operational Data** (PostgreSQL):
   - Recent data (30-90 days)
   - High write throughput with UPSERT
   - Indexed for fast queries

b) **Analytical Data** (Parquet/Columnar):
   - Historical snapshots
   - Compressed (10x+ space savings)
   - Stored in S3/GCS
   - Query with Athena/BigQuery/Presto

c) **Example Schema**:
```
/data/
  /operational/          # PostgreSQL (hot data)
    repositories         # Last 30 days
  /archive/              # S3 Parquet (cold data)
    /year=2024/
      /month=01/
        /day=01/
          repositories.parquet
```

#### 6. Infrastructure and Deployment

**Current**: Single GitHub Actions runner

**500M Scale**: Kubernetes cluster

```yaml
# Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: github-crawler
spec:
  replicas: 20  # 20 crawler workers
  template:
    spec:
      containers:
      - name: crawler
        image: github-crawler:latest
        env:
        - name: WORKER_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crawler-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: github-crawler
  minReplicas: 10
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

#### 7. Monitoring and Observability

**Required at 500M Scale**:

- **Metrics**: Prometheus + Grafana
  - Crawl rate (repos/sec)
  - API rate limit usage
  - Database query performance
  - Queue depth
  - Error rates

- **Logging**: ELK Stack or Loki
  - Structured JSON logs
  - Centralized aggregation
  - Query and alert on errors

- **Tracing**: Jaeger or Tempo
  - Distributed tracing across workers
  - Identify bottlenecks

- **Alerting**: PagerDuty or OpsGenie
  - Rate limit exhaustion
  - Database connection pool exhaustion
  - Worker failures
  - Queue backlog

#### 8. Cost Optimization

**Estimated Costs at 500M Scale**:

| Resource | Specification | Monthly Cost |
|----------|--------------|--------------|
| Database (RDS) | db.r6g.2xlarge | $600 |
| Worker Instances | 20x c6g.large | $1,200 |
| Load Balancer | ALB | $50 |
| S3 Storage | 5TB | $115 |
| Data Transfer | 1TB/month | $90 |
| Message Queue | SQS/RabbitMQ | $50 |
| **Total** | | **~$2,100/month** |

**Optimizations**:
- Use spot instances for workers (60% savings)
- Reserved instances for database (40% savings)
- Compress stored data (10x reduction)
- Optimize query patterns to reduce I/O

**Optimized Total**: ~$900-1,200/month

#### 9. Reliability and Fault Tolerance

**Idempotency**:
```python
# Each crawl operation must be idempotent
@dataclass
class CrawlTask:
    task_id: str  # Unique ID for deduplication
    owner_prefix: str  # e.g., "A-C"
    retry_count: int = 0
    
# Worker ensures same task isn't processed twice
async def process_task(task: CrawlTask):
    if await redis.exists(f"processed:{task.task_id}"):
        return  # Already processed
    
    await crawl_repositories(task)
    
    await redis.setex(
        f"processed:{task.task_id}",
        86400,  # 24 hour TTL
        "1"
    )
```

**Circuit Breakers**:
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_github_api():
    """
    If 5 consecutive failures, circuit opens.
    Wait 60 seconds before trying again.
    """
    pass
```

**Checkpointing**:
```python
# Save progress regularly
async def crawl_with_checkpoints():
    checkpoint = await load_checkpoint()
    
    async for repo in fetch_repositories(start_cursor=checkpoint.cursor):
        await save_repository(repo)
        
        if repo.count % 1000 == 0:
            await save_checkpoint(Checkpoint(
                cursor=current_cursor,
                count=repo.count,
                timestamp=datetime.now()
            ))
```

---

## Schema Evolution for Additional Metadata

### Design Principles

1. **Foreign Key Hierarchy**: All metadata references `repositories(id)`
2. **Natural Unique Constraints**: Prevent duplicates efficiently
3. **Minimal Write Amplification**: Updates only affect changed tables
4. **Temporal Tracking**: Separate `created_at` from `updated_at`
5. **Efficient Queries**: Index foreign keys and common query patterns

### Example: Complete Metadata Schema

```sql
-- Core table (already exists)
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

-- Issues
CREATE TABLE issues (
    id SERIAL PRIMARY KEY,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    issue_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    state VARCHAR(50) NOT NULL CHECK (state IN ('open', 'closed')),
    author VARCHAR(255) NOT NULL,
    comment_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    crawled_at TIMESTAMP NOT NULL,
    CONSTRAINT issues_repo_number_unique UNIQUE (repository_id, issue_number)
);

CREATE INDEX idx_issues_repository_id ON issues(repository_id);
CREATE INDEX idx_issues_state ON issues(state);
CREATE INDEX idx_issues_updated_at ON issues(updated_at DESC);

-- Pull Requests
CREATE TABLE pull_requests (
    id SERIAL PRIMARY KEY,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    pr_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    state VARCHAR(50) NOT NULL CHECK (state IN ('open', 'closed', 'merged')),
    author VARCHAR(255) NOT NULL,
    comment_count INTEGER NOT NULL DEFAULT 0,
    commit_count INTEGER NOT NULL DEFAULT 0,
    changed_files INTEGER NOT NULL DEFAULT 0,
    additions INTEGER NOT NULL DEFAULT 0,
    deletions INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    merged_at TIMESTAMP,
    crawled_at TIMESTAMP NOT NULL,
    CONSTRAINT pr_repo_number_unique UNIQUE (repository_id, pr_number)
);

CREATE INDEX idx_pr_repository_id ON pull_requests(repository_id);
CREATE INDEX idx_pr_state ON pull_requests(state);
CREATE INDEX idx_pr_updated_at ON pull_requests(updated_at DESC);

-- Comments (polymorphic - can belong to issue or PR)
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    issue_id INTEGER REFERENCES issues(id) ON DELETE CASCADE,
    pull_request_id INTEGER REFERENCES pull_requests(id) ON DELETE CASCADE,
    comment_number INTEGER NOT NULL,  -- Sequential per parent
    author VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    crawled_at TIMESTAMP NOT NULL,
    CONSTRAINT comment_parent_check CHECK (
        (issue_id IS NOT NULL AND pull_request_id IS NULL) OR
        (issue_id IS NULL AND pull_request_id IS NOT NULL)
    ),
    CONSTRAINT comment_unique UNIQUE (issue_id, pull_request_id, comment_number)
);

CREATE INDEX idx_comments_issue_id ON comments(issue_id);
CREATE INDEX idx_comments_pr_id ON comments(pull_request_id);

-- Commits (can be standalone or part of PR)
CREATE TABLE commits (
    id SERIAL PRIMARY KEY,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    sha VARCHAR(40) NOT NULL,  -- Git SHA
    author VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    additions INTEGER NOT NULL DEFAULT 0,
    deletions INTEGER NOT NULL DEFAULT 0,
    changed_files INTEGER NOT NULL DEFAULT 0,
    committed_at TIMESTAMP NOT NULL,
    crawled_at TIMESTAMP NOT NULL,
    CONSTRAINT commits_repo_sha_unique UNIQUE (repository_id, sha)
);

CREATE INDEX idx_commits_repository_id ON commits(repository_id);
CREATE INDEX idx_commits_sha ON commits(sha);
CREATE INDEX idx_commits_committed_at ON commits(committed_at DESC);

-- PR Commits (junction table)
CREATE TABLE pull_request_commits (
    pull_request_id INTEGER NOT NULL REFERENCES pull_requests(id) ON DELETE CASCADE,
    commit_id INTEGER NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    commit_order INTEGER NOT NULL,  -- Order in PR
    PRIMARY KEY (pull_request_id, commit_id)
);

CREATE INDEX idx_pr_commits_pr_id ON pull_request_commits(pull_request_id);
CREATE INDEX idx_pr_commits_commit_id ON pull_request_commits(commit_id);

-- Reviews (on pull requests)
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    pull_request_id INTEGER NOT NULL REFERENCES pull_requests(id) ON DELETE CASCADE,
    reviewer VARCHAR(255) NOT NULL,
    state VARCHAR(50) NOT NULL CHECK (state IN ('approved', 'changes_requested', 'commented', 'dismissed')),
    body TEXT,
    submitted_at TIMESTAMP NOT NULL,
    crawled_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_reviews_pr_id ON reviews(pull_request_id);
CREATE INDEX idx_reviews_state ON reviews(state);

-- CI Checks (per commit)
CREATE TABLE ci_checks (
    id SERIAL PRIMARY KEY,
    commit_id INTEGER NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    check_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'success', 'failure', 'error', 'cancelled')),
    conclusion VARCHAR(50),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    crawled_at TIMESTAMP NOT NULL,
    CONSTRAINT ci_checks_commit_name_unique UNIQUE (commit_id, check_name)
);

CREATE INDEX idx_ci_checks_commit_id ON ci_checks(commit_id);
CREATE INDEX idx_ci_checks_status ON ci_checks(status);
```

### Efficient Update Patterns

#### Scenario 1: PR Gets New Comments (10 → 30 total)

**Before**:
```
repositories: 1 row (star_count: 1000)
pull_requests: 1 row (pr_number: 42, comment_count: 10)
comments: 10 rows (for this PR)
```

**After**:
```sql
-- Insert only the NEW comments (20 rows affected)
INSERT INTO comments (pull_request_id, comment_number, author, body, created_at, updated_at, crawled_at)
VALUES 
    (42, 11, 'user1', 'Great work!', '2024-01-15', '2024-01-15', '2024-01-15'),
    (42, 12, 'user2', 'Needs changes', '2024-01-15', '2024-01-15', '2024-01-15'),
    -- ... 18 more rows
    (42, 30, 'user20', 'LGTM', '2024-01-15', '2024-01-15', '2024-01-15');

-- Update only the PR record (1 row affected)
UPDATE pull_requests 
SET comment_count = 30, updated_at = CURRENT_TIMESTAMP, crawled_at = CURRENT_TIMESTAMP
WHERE id = 42;

-- Repository record: UNCHANGED (0 rows affected)
```

**Total Impact**: 21 rows affected (20 inserts + 1 update)

#### Scenario 2: New CI Check Result

**Before**:
```
commits: 1 row (sha: abc123)
ci_checks: 3 rows (for this commit)
```

**After**:
```sql
-- Insert or update the single CI check
INSERT INTO ci_checks (commit_id, check_name, status, conclusion, completed_at, crawled_at)
VALUES (123, 'tests', 'success', 'success', '2024-01-15 10:30:00', '2024-01-15 10:30:00')
ON CONFLICT (commit_id, check_name)
DO UPDATE SET
    status = EXCLUDED.status,
    conclusion = EXCLUDED.conclusion,
    completed_at = EXCLUDED.completed_at,
    crawled_at = EXCLUDED.crawled_at;

-- Commit, PR, and repository records: UNCHANGED
```

**Total Impact**: 1 row affected (1 upsert)

#### Scenario 3: Daily Star Count Update for 100K Repos

```sql
-- Bulk upsert using temporary table
CREATE TEMP TABLE repo_updates (
    owner VARCHAR(255),
    name VARCHAR(255),
    star_count INTEGER,
    crawled_at TIMESTAMP
);

-- Load data (100,000 rows)
COPY repo_updates FROM STDIN;

-- Efficient update (only repos with changed star count)
UPDATE repositories r
SET 
    star_count = u.star_count,
    crawled_at = u.crawled_at,
    updated_at = CURRENT_TIMESTAMP
FROM repo_updates u
WHERE r.owner = u.owner 
  AND r.name = u.name
  AND r.star_count != u.star_count;  -- Only update if changed

-- Typical result: ~5,000 rows affected (5% of repos change daily)
```

### Migration Strategy for Adding New Metadata

```sql
-- Step 1: Create new table (zero downtime, no locks)
CREATE TABLE issues (
    ...
);

-- Step 2: Deploy application code that writes to new table
-- (old code continues working, new code also writes new data)

-- Step 3: Backfill historical data (background job, batched)
DO $$
DECLARE
    batch_size INT := 10000;
    offset_val INT := 0;
BEGIN
    LOOP
        -- Fetch and insert in batches
        INSERT INTO issues (repository_id, issue_number, ...)
        SELECT ...
        FROM external_source
        LIMIT batch_size OFFSET offset_val;
        
        EXIT WHEN NOT FOUND;
        offset_val := offset_val + batch_size;
        
        -- Small delay to avoid overwhelming database
        PERFORM pg_sleep(0.1);
    END LOOP;
END $$;

-- Step 4: Add constraints after backfill complete
ALTER TABLE issues ADD CONSTRAINT issues_repo_number_unique UNIQUE (repository_id, issue_number);
CREATE INDEX idx_issues_repository_id ON issues(repository_id);

-- Step 5: Remove old backfill code
```

### Query Patterns

**Get repository with all metadata counts**:
```sql
SELECT 
    r.full_name,
    r.star_count,
    COUNT(DISTINCT i.id) as issue_count,
    COUNT(DISTINCT pr.id) as pr_count,
    COUNT(DISTINCT c.id) as commit_count
FROM repositories r
LEFT JOIN issues i ON i.repository_id = r.id
LEFT JOIN pull_requests pr ON pr.repository_id = r.id
LEFT JOIN commits c ON c.repository_id = r.id
WHERE r.owner = 'facebook' AND r.name = 'react'
GROUP BY r.id;
```

**Get PRs with comment counts (efficient)**:
```sql
SELECT 
    pr.pr_number,
    pr.title,
    pr.comment_count,  -- Pre-aggregated, no need to count
    pr.state
FROM pull_requests pr
WHERE pr.repository_id = 123
  AND pr.state = 'open'
ORDER BY pr.updated_at DESC
LIMIT 50;
```

**Get active PRs (with recent comments)**:
```sql
SELECT DISTINCT
    pr.pr_number,
    pr.title,
    pr.updated_at,
    pr.comment_count
FROM pull_requests pr
WHERE pr.repository_id = 123
  AND pr.state = 'open'
  AND pr.updated_at > NOW() - INTERVAL '7 days'
ORDER BY pr.updated_at DESC;
```

### Summary: Schema Evolution Benefits

✅ **Efficient Updates**: Only affected tables/rows are modified  
✅ **Flexible**: Easy to add new metadata types without schema changes to existing tables  
✅ **Scalable**: Partitioning and sharding strategies apply cleanly  
✅ **Performant**: Counts pre-aggregated, indexes on foreign keys  
✅ **Maintainable**: Clear foreign key relationships, normalized design  
✅ **Queryable**: Supports both detail queries and aggregations efficiently  

This design supports continuous evolution while maintaining high performance at scale.

