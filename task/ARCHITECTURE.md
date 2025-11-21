# Architecture Documentation

## Clean Architecture Overview

This project follows **Clean Architecture** (Hexagonal Architecture) principles to ensure maintainability, testability, and independence from external frameworks.

## Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Entry Points                              │
│         (crawl_stars.py, GitHub Actions)                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  Application Layer                           │
│                                                              │
│  ┌────────────────────────────────────────────────┐         │
│  │         CrawlerService                          │         │
│  │  (Orchestrates crawling operation)             │         │
│  └────────────────────────────────────────────────┘         │
│                                                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Domain Layer (Core)                       │
│                                                              │
│  ┌─────────────────────┐  ┌────────────────────────┐        │
│  │   Domain Models     │  │   Interfaces (Ports)   │        │
│  │                     │  │                        │        │
│  │  • Repository       │  │  • IGitHubClient       │        │
│  │  • CrawlMetrics     │  │  • IRepositoryStorage  │        │
│  └─────────────────────┘  └────────────────────────┘        │
│                                                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Infrastructure Layer (Adapters)                 │
│                                                              │
│  ┌──────────────────────────┐  ┌────────────────────────┐   │
│  │  GitHubGraphQLClient     │  │ PostgresRepository     │   │
│  │  (implements             │  │ (implements            │   │
│  │   IGitHubClient)         │  │  IRepositoryStorage)   │   │
│  └──────────────────────────┘  └────────────────────────┘   │
│                                                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│               External Systems                               │
│                                                              │
│  ┌──────────────────────────┐  ┌────────────────────────┐   │
│  │   GitHub GraphQL API     │  │    PostgreSQL          │   │
│  └──────────────────────────┘  └────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Dependency Rule

**Dependencies point INWARD only:**

- Infrastructure → Domain (adapters implement domain interfaces)
- Application → Domain (use cases depend on domain models and interfaces)
- Domain → Nothing (core business logic has no external dependencies)

## Layer Responsibilities

### Domain Layer (`src/domain/`)

**Purpose**: Core business logic, entities, and interfaces (ports)

**Contents**:
- `models.py`: Immutable domain entities (Repository, CrawlMetrics)
- `github_interface.py`: Port for GitHub API operations
- `repository_interface.py`: Port for data persistence

**Characteristics**:
- No external dependencies
- Framework-agnostic
- Testable without infrastructure
- Represents business concepts

**Example**:
```python
@dataclass(frozen=True)
class Repository:
    """Immutable domain entity."""
    owner: str
    name: str
    star_count: int
    crawled_at: datetime
    
    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"
```

### Application Layer (`src/application/`)

**Purpose**: Use cases and orchestration logic

**Contents**:
- `crawler_service.py`: Coordinates GitHub fetching and database storage

**Characteristics**:
- Depends only on domain interfaces (not implementations)
- No knowledge of HTTP, GraphQL, SQL, etc.
- Orchestrates domain objects
- Transaction boundaries

**Example**:
```python
class CrawlerService:
    def __init__(
        self,
        github_client: IGitHubClient,  # Port, not implementation
        storage: IRepositoryStorage     # Port, not implementation
    ):
        self._github_client = github_client
        self._storage = storage
    
    async def crawl_repositories(self, count: int) -> CrawlMetrics:
        # Orchestration logic using domain interfaces
        pass
```

### Infrastructure Layer (`src/infrastructure/`)

**Purpose**: Adapters for external systems

**Contents**:
- `github_client.py`: GitHub GraphQL API adapter (implements `IGitHubClient`)
- `postgres_repository.py`: PostgreSQL adapter (implements `IRepositoryStorage`)

**Characteristics**:
- Implements domain interfaces
- Contains framework-specific code
- Handles external system details (HTTP, SQL, etc.)
- Translates between external formats and domain models

**Example**:
```python
class GitHubGraphQLClient(IGitHubClient):
    """Adapter implementing the IGitHubClient port."""
    
    async def fetch_repositories(self, count: int) -> AsyncIterator[Repository]:
        # GraphQL-specific implementation
        # Translates GitHub API response to Repository domain entity
        pass
```

## Anti-Corruption Layer

The infrastructure layer acts as an **anti-corruption layer** preventing external system details from leaking into the domain:

```python
# GitHub API returns this:
{
    "owner": {"login": "facebook"},
    "name": "react",
    "stargazerCount": 200000
}

# Infrastructure layer transforms it to domain entity:
Repository(
    owner="facebook",
    name="react",
    star_count=200000,
    crawled_at=datetime.now()
)
```

## Benefits of This Architecture

### 1. **Testability**

Domain and application layers can be tested without real GitHub API or database:

```python
# Mock implementations for testing
class MockGitHubClient(IGitHubClient):
    async def fetch_repositories(self, count: int):
        yield Repository(owner="test", name="repo", star_count=100, crawled_at=datetime.now())

# Test application logic without external dependencies
def test_crawler_service():
    mock_client = MockGitHubClient()
    mock_storage = MockStorage()
    service = CrawlerService(mock_client, mock_storage)
    # Test business logic...
```

### 2. **Flexibility**

Easy to swap implementations:

```python
# Development: Use mock implementations
dev_client = MockGitHubClient()

# Production: Use real implementations
prod_client = GitHubGraphQLClient(token)

# Testing: Use in-memory storage
test_storage = InMemoryStorage()

# Production: Use PostgreSQL
prod_storage = PostgresRepositoryStorage(conn_string)

# Service doesn't care which implementation
service = CrawlerService(client, storage)
```

### 3. **Maintainability**

Changes to external systems don't affect core logic:

- GitHub API changes → Only update `GitHubGraphQLClient`
- Database migration → Only update `PostgresRepositoryStorage`
- Add new storage backend → Create new adapter implementing `IRepositoryStorage`

### 4. **Business Logic Focus**

Domain layer contains pure business logic:

```python
# Domain entity method - pure business logic
def with_increased_stars(self, increment: int) -> 'Repository':
    return Repository(
        owner=self.owner,
        name=self.name,
        star_count=self.star_count + increment,
        crawled_at=self.crawled_at,
        repo_id=self.repo_id
    )
```

## Design Patterns Used

### 1. **Repository Pattern**

`IRepositoryStorage` interface abstracts data persistence:

```python
class IRepositoryStorage(ABC):
    @abstractmethod
    def save_repositories(self, repositories: List[Repository]) -> None:
        pass
```

### 2. **Adapter Pattern**

Infrastructure classes adapt external systems to domain interfaces:

```
Domain Interface (Port) → Infrastructure Adapter → External System
    IGitHubClient       → GitHubGraphQLClient    → GitHub API
```

### 3. **Dependency Injection**

Dependencies injected via constructor (IoC):

```python
# Composition root (main entry point)
client = GitHubGraphQLClient(token)
storage = PostgresRepositoryStorage(conn)
service = CrawlerService(client, storage)
```

### 4. **Immutability**

Domain entities are immutable (frozen dataclasses):

```python
@dataclass(frozen=True)  # Immutable
class Repository:
    owner: str
    name: str
    star_count: int
```

Benefits:
- Thread-safe
- No unexpected mutations
- Easier to reason about

### 5. **Strategy Pattern**

Different crawling strategies can be implemented:

```python
class ICrawlStrategy(ABC):
    @abstractmethod
    async def crawl(self) -> List[Repository]:
        pass

class StarBasedCrawlStrategy(ICrawlStrategy):
    async def crawl(self):
        # Crawl by star count
        pass

class LanguageBasedCrawlStrategy(ICrawlStrategy):
    async def crawl(self):
        # Crawl by programming language
        pass
```

## Code Flow Example

**User Request**: Crawl 100,000 repositories

```
1. crawl_stars.py (Entry Point)
   ↓
2. CrawlerService.crawl_repositories() (Application)
   ↓
3. IGitHubClient.fetch_repositories() (Domain Interface)
   ↓
4. GitHubGraphQLClient.fetch_repositories() (Infrastructure)
   ↓
5. GitHub GraphQL API (External)
   ↓
6. Transform to Repository entities (Infrastructure → Domain)
   ↓
7. IRepositoryStorage.save_repositories() (Domain Interface)
   ↓
8. PostgresRepositoryStorage.save_repositories() (Infrastructure)
   ↓
9. PostgreSQL Database (External)
```

## Testing Strategy

### Unit Tests (Domain Layer)

```python
def test_repository_full_name():
    repo = Repository(owner="facebook", name="react", ...)
    assert repo.full_name == "facebook/react"
```

### Integration Tests (Application Layer)

```python
async def test_crawler_service_with_mocks():
    mock_client = MockGitHubClient()
    mock_storage = MockStorage()
    service = CrawlerService(mock_client, mock_storage)
    
    metrics = await service.crawl_repositories(100)
    
    assert metrics.repositories_crawled == 100
    assert mock_storage.get_repository_count() == 100
```

### End-to-End Tests

```python
async def test_full_crawl_pipeline():
    # Use real implementations against test database
    client = GitHubGraphQLClient(test_token)
    storage = PostgresRepositoryStorage(test_db_connection)
    service = CrawlerService(client, storage)
    
    metrics = await service.crawl_repositories(10)
    
    assert metrics.repositories_crawled == 10
    assert storage.get_repository_count() == 10
```

## Comparison: Clean vs Traditional Architecture

### Traditional (Layered) Architecture

```
Presentation → Business Logic → Data Access → Database
```

**Problems**:
- Business logic depends on database (hard to test)
- Framework-specific code mixed with business rules
- Hard to swap implementations
- Tight coupling

### Clean Architecture (This Project)

```
Infrastructure → Application → Domain ← Application ← Infrastructure
```

**Benefits**:
- Business logic independent of frameworks
- Easy to test (mock external dependencies)
- Easy to swap implementations
- Loose coupling via interfaces

## Key Takeaways

1. **Domain at the center**: Core business logic has no external dependencies
2. **Dependency inversion**: High-level policies don't depend on low-level details
3. **Interfaces define contracts**: Domain defines what it needs, infrastructure provides it
4. **Immutability**: Domain entities are immutable for safety and clarity
5. **Testability**: Each layer can be tested independently
6. **Flexibility**: Easy to swap implementations without changing business logic

This architecture ensures the codebase remains maintainable, testable, and adaptable to changing requirements.

