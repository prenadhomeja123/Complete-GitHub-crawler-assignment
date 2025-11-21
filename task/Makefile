.PHONY: help install setup-db crawl export test clean verify stats

help:
	@echo "GitHub Crawler - Available Commands"
	@echo ""
	@echo "  make install    - Install Python dependencies"
	@echo "  make verify     - Verify setup is correct"
	@echo "  make setup-db   - Initialize PostgreSQL database schema"
	@echo "  make crawl      - Run the GitHub crawler"
	@echo "  make export     - Export database to CSV"
	@echo "  make stats      - Display statistics about crawled data"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Clean generated files"
	@echo ""

install:
	pip install --upgrade pip
	pip install -r requirements.txt

verify:
	python scripts/verify_setup.py

setup-db:
	python setup_postgres.py

crawl:
	python crawl_stars.py

export:
	python export_database.py repositories.csv

stats:
	python scripts/query_stats.py

test:
	pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -f repositories.csv

