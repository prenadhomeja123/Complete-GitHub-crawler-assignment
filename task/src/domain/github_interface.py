"""GitHub API interface (port) for fetching repository data.

This is the anti-corruption layer that shields the domain from GitHub API specifics.
"""
from abc import ABC, abstractmethod
from typing import List, AsyncIterator
from src.domain.models import Repository


class IGitHubClient(ABC):
    """Abstract interface for GitHub API operations."""
    
    @abstractmethod
    async def fetch_repositories(self, count: int) -> AsyncIterator[Repository]:
        """Fetch repositories from GitHub.
        
        Args:
            count: Number of repositories to fetch
            
        Yields:
            Repository entities
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close any open connections."""
        pass

