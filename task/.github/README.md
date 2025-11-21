# GitHub Actions Workflow

This directory contains the automated CI/CD pipeline for the GitHub crawler.

## Workflow: `crawl.yml`

### What It Does

1. **Spins up PostgreSQL** service container
2. **Sets up Python** 3.11 environment
3. **Installs dependencies** from requirements.txt
4. **Creates database schema** using setup_postgres.py
5. **Crawls 100,000 repositories** from GitHub
6. **Exports results** to CSV
7. **Uploads CSV** as a workflow artifact

### Triggers

- **Manual**: Actions tab → "GitHub Repository Crawler" → "Run workflow"
- **Scheduled**: Daily at 2 AM UTC (configurable in `on.schedule`)
- **Push**: Can be enabled by adding `push` trigger

### Environment Variables

The workflow uses:
- `GITHUB_TOKEN` - Automatically provided by GitHub (no setup needed!)
- `POSTGRES_*` - Configured for the service container
- `TARGET_REPO_COUNT` - Number of repos to crawl (default: 100,000)

### Running Manually

1. Go to the **Actions** tab in your repository
2. Select **"GitHub Repository Crawler"** from the left sidebar
3. Click **"Run workflow"** button (top right)
4. Select branch (usually `main`)
5. Click green **"Run workflow"** button

### Viewing Results

After the workflow completes (15-30 minutes):

1. Click on the workflow run
2. Scroll to **Artifacts** section at the bottom
3. Download **"crawled-repositories"** artifact
4. Unzip to get `repositories.csv`

### Monitoring Progress

Click on a running workflow to see live logs:
- **Setup steps**: Quick (1-2 minutes)
- **Crawl step**: Longest (15-30 minutes)
  - Watch for "Fetched X/100000 repositories" progress
  - Rate limit info is logged
- **Export step**: Quick (1-2 minutes)

### Customizing

Edit `.github/workflows/crawl.yml`:

```yaml
# Change target repository count
env:
  TARGET_REPO_COUNT: 50000  # Crawl fewer repos

# Change schedule (cron syntax)
schedule:
  - cron: '0 6 * * *'  # Run at 6 AM UTC daily

# Add workflow_dispatch inputs
workflow_dispatch:
  inputs:
    repo_count:
      description: 'Number of repositories to crawl'
      required: false
      default: '100000'
```

### Troubleshooting

**Workflow fails with rate limit error:**
- The crawler automatically handles rate limits
- If failing, reduce `TARGET_REPO_COUNT`
- Standard token: 5,000 requests/hour
- 100 repos per request = ~50 requests needed for 5,000 repos

**Database connection fails:**
- Service container should start automatically
- Check "Initialize containers" step in logs
- Verify PostgreSQL health checks pass

**Artifact not uploaded:**
- Check export step logs
- Verify crawler completed successfully
- Artifact retention: 30 days (configurable)

### Service Container Details

PostgreSQL configuration:
- **Image**: `postgres:16`
- **Port**: 5432
- **Database**: github_crawler
- **User**: postgres
- **Password**: postgres
- **Health checks**: Automatic

### Permissions

The workflow uses **default permissions**:
- Read repository contents
- Write workflow artifacts
- No elevated permissions needed
- No secrets required (uses automatic GITHUB_TOKEN)

### Cost

GitHub Actions is **free for public repositories**:
- 2,000 minutes/month for private repos (free tier)
- This workflow uses ~30-60 minutes per run
- Artifacts stored for 30 days (configurable)

### Extending the Workflow

Add additional steps:

```yaml
- name: Run tests
  run: pytest tests/ -v

- name: Generate report
  run: python scripts/generate_report.py

- name: Deploy results
  run: |
    # Upload to S3, BigQuery, etc.
```

### Best Practices

1. **Test locally first**: Run `make crawl` before pushing
2. **Start small**: Test with 100 repos before full 100K
3. **Monitor logs**: Watch for errors during first run
4. **Check artifacts**: Verify CSV contents are correct
5. **Adjust schedule**: Set appropriate frequency for your needs

### Example Successful Run

```
✅ Checkout code
✅ Set up Python
✅ Install dependencies
✅ Setup PostgreSQL schema
✅ Crawl GitHub repositories (25m 30s)
   └─ Fetched 100,000 repositories
✅ Export database to CSV
✅ Upload artifact
```

Artifact: `repositories.csv` (5-10 MB)

### Next Steps

After successful run:
1. Download and analyze CSV
2. Query database (if persistent)
3. Visualize trends
4. Schedule regular runs
5. Extend with more metadata

## Support

See main README.md for detailed documentation.

