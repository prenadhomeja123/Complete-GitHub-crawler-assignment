# Contributing to GitHub Crawler

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Code of Conduct

Please be respectful and constructive in all interactions.

## Architecture Principles

This project follows **Clean Architecture** principles. Before contributing, please review:

- `ARCHITECTURE.md` - Detailed architecture documentation
- `README.md` - Project overview and setup

### Key Principles to Follow

1. **Dependency Inversion**: Domain layer has no external dependencies
2. **Separation of Concerns**: Each module has a single, well-defined responsibility
3. **Immutability**: Domain entities are immutable (use frozen dataclasses)
4. **Interface Segregation**: Keep interfaces focused and minimal
5. **Anti-Corruption Layer**: Infrastructure adapters translate between external systems and domain

## Project Structure

```
github-crawler/
├── src/
│   ├── domain/          # Core business logic (no external dependencies)
│   ├── application/     # Use cases and orchestration
│   └── infrastructure/  # Adapters for external systems
├── tests/               # Test suite
├── setup_postgres.py    # Database initialization
├── crawl_stars.py       # Main entry point
└── export_database.py   # Export utility
```

## Development Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- GitHub Personal Access Token

### Local Setup

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/github-crawler.git
cd github-crawler
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
make install
# or
pip install -r requirements.txt
```

4. **Set up environment variables**:
```bash
cp env.example .env
# Edit .env with your configuration
```

5. **Start PostgreSQL** (example using Docker):
```bash
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=github_crawler \
  -p 5432:5432 \
  postgres:16
```

6. **Initialize database**:
```bash
make setup-db
```

## Making Changes

### Workflow

1. **Create a branch**:
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes** following the architecture principles

3. **Write tests** for new functionality

4. **Run tests**:
```bash
make test
```

5. **Commit your changes**:
```bash
git add .
git commit -m "feat: add your feature description"
```

6. **Push and create a pull request**:
```bash
git push origin feature/your-feature-name
```

## Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Maintenance tasks

**Examples**:
```
feat: add rate limit monitoring
fix: handle null values in repository name
docs: update scaling documentation
refactor: extract rate limiter to separate class
test: add unit tests for domain models
```

## Code Style

### Python Style Guide

- Follow [PEP 8](https://pep8.org/)
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use descriptive variable and function names

### Formatting

```bash
# Format code with black
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/
```

### Example Good Code

```python
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Repository:
    """Immutable domain entity representing a GitHub repository.
    
    Args:
        owner: Repository owner username
        name: Repository name
        star_count: Number of stars
        crawled_at: Timestamp when data was crawled
    """
    owner: str
    name: str
    star_count: int
    crawled_at: datetime
    
    @property
    def full_name(self) -> str:
        """Returns the full repository name (owner/name)."""
        return f"{self.owner}/{self.name}"
```

## Testing

### Writing Tests

- Place tests in `tests/` directory
- Mirror the source structure
- Use descriptive test names

**Example**:

```python
# tests/test_domain_models.py
def test_repository_full_name():
    """Test that full_name property returns owner/name format."""
    repo = Repository(
        owner="facebook",
        name="react",
        star_count=200000,
        crawled_at=datetime.now()
    )
    
    assert repo.full_name == "facebook/react"
```

### Test Categories

1. **Unit Tests** (Domain Layer):
   - Test business logic in isolation
   - No external dependencies
   - Fast execution

2. **Integration Tests** (Application Layer):
   - Test use cases with mocked infrastructure
   - Verify interaction between components

3. **End-to-End Tests**:
   - Test full pipeline
   - Use test database
   - Can be slower

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_domain_models.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Adding New Features

### Example: Adding a New Data Source

1. **Define domain interface** (`src/domain/new_interface.py`):
```python
from abc import ABC, abstractmethod

class INewDataSource(ABC):
    @abstractmethod
    async def fetch_data(self) -> List[SomeEntity]:
        pass
```

2. **Create infrastructure adapter** (`src/infrastructure/new_adapter.py`):
```python
from src.domain.new_interface import INewDataSource

class NewAdapter(INewDataSource):
    async def fetch_data(self) -> List[SomeEntity]:
        # Implementation details
        pass
```

3. **Update application service** (`src/application/`):
```python
class EnhancedCrawlerService:
    def __init__(
        self,
        github_client: IGitHubClient,
        new_source: INewDataSource,  # New dependency
        storage: IRepositoryStorage
    ):
        self._github_client = github_client
        self._new_source = new_source
        self._storage = storage
```

4. **Write tests**:
```python
def test_new_data_source():
    mock_source = MockNewDataSource()
    # Test implementation...
```

### Example: Extending the Schema

1. **Add migration script** (`migrations/001_add_issues_table.sql`):
```sql
CREATE TABLE issues (
    id SERIAL PRIMARY KEY,
    repository_id INTEGER NOT NULL REFERENCES repositories(id),
    issue_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    -- ... other fields
    CONSTRAINT issues_repo_number_unique UNIQUE (repository_id, issue_number)
);
```

2. **Update setup script** (`setup_postgres.py`):
```python
def create_schema(conn):
    # ... existing code ...
    
    # Add new table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (...)
    """)
```

3. **Create domain model**:
```python
@dataclass(frozen=True)
class Issue:
    repository_id: int
    issue_number: int
    title: str
    state: str
```

4. **Update repository interface**:
```python
class IRepositoryStorage(ABC):
    # ... existing methods ...
    
    @abstractmethod
    def save_issues(self, issues: List[Issue]) -> None:
        pass
```

## Pull Request Guidelines

### Before Submitting

- [ ] Tests pass locally (`make test`)
- [ ] Code follows style guidelines
- [ ] Documentation updated (if needed)
- [ ] Commit messages follow convention
- [ ] No merge conflicts with main branch

### PR Description Template

```markdown
## Description
Brief description of changes

## Motivation
Why are these changes needed?

## Changes Made
- Change 1
- Change 2

## Testing
How was this tested?

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Follows architecture principles
- [ ] No breaking changes (or documented if necessary)
```

## Reporting Issues

When reporting bugs, please include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: Detailed steps to reproduce the problem
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**: OS, Python version, PostgreSQL version
6. **Logs**: Relevant error messages or logs

## Questions?

- Open an issue for general questions
- Tag with `question` label
- Check existing issues first

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

