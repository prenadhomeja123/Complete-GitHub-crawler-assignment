"""Tests for domain models."""
from datetime import datetime
from src.domain.models import Repository, CrawlMetrics


def test_repository_creation():
    """Test creating an immutable Repository entity."""
    repo = Repository(
        owner="facebook",
        name="react",
        star_count=200000,
        crawled_at=datetime(2024, 1, 1, 12, 0, 0)
    )
    
    assert repo.owner == "facebook"
    assert repo.name == "react"
    assert repo.full_name == "facebook/react"
    assert repo.star_count == 200000
    assert repo.repo_id is None


def test_repository_with_id():
    """Test adding ID to repository."""
    repo = Repository(
        owner="facebook",
        name="react",
        star_count=200000,
        crawled_at=datetime(2024, 1, 1, 12, 0, 0)
    )
    
    repo_with_id = repo.with_id(42)
    
    assert repo_with_id.repo_id == 42
    assert repo_with_id.owner == repo.owner
    assert repo.repo_id is None  # Original unchanged (immutability)


def test_crawl_metrics():
    """Test creating CrawlMetrics."""
    metrics = CrawlMetrics(
        repositories_crawled=100000,
        duration_seconds=1800.5,
        rate_limit_resets=3,
        errors_encountered=0
    )
    
    assert metrics.repositories_crawled == 100000
    assert metrics.duration_seconds == 1800.5
    assert metrics.rate_limit_resets == 3
    assert metrics.errors_encountered == 0

