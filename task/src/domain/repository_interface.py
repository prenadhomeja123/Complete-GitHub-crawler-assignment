"""Repository interface (port) for data persistence.

This is the port in hexagonal architecture that the infrastructure layer implements.
"""
from abc import ABC, abstractmethod
from typing import List
from src.domain.models import Repository


class IRepositoryStorage(ABC):
    """Abstract interface for repository data storage."""
    
    @abstractmethod
    def save_repositories(self, repositories: List[Repository]) -> None:
        """Save or update repositories in storage.
        
        Should be an efficient upsert operation that updates existing records
        and inserts new ones.
        
        Args:
            repositories: List of Repository entities to persist
        """
        pass
    
    @abstractmethod
    def get_repository_count(self) -> int:
        """Get the total number of repositories in storage."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close any open connections."""
        pass

