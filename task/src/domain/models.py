"""Domain models representing core business entities."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Repository:
    """Immutable domain entity representing a GitHub repository.
    
    Using frozen dataclass for immutability following clean architecture principles.
    """
    owner: str
    name: str
    star_count: int
    crawled_at: datetime
    repo_id: Optional[int] = None
    
    @property
    def full_name(self) -> str:
        """Returns the full repository name (owner/name)."""
        return f"{self.owner}/{self.name}"
    
    def with_id(self, repo_id: int) -> 'Repository':
        """Returns a new Repository instance with the provided ID."""
        return Repository(
            owner=self.owner,
            name=self.name,
            star_count=self.star_count,
            crawled_at=self.crawled_at,
            repo_id=repo_id
        )


@dataclass(frozen=True)
class CrawlMetrics:
    """Metrics for a crawl operation."""
    repositories_crawled: int
    duration_seconds: float
    rate_limit_resets: int
    errors_encountered: int

