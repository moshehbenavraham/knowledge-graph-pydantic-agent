# Core Development
setup:
	python -m pip install -e .[dev]
	pre-commit install

check:
	ruff check src/ tests/
	mypy src/ tests/
	pytest tests/

format:
	black src/ tests/
	ruff check --fix src/ tests/

test:
	pytest tests/

test-coverage:
	pytest --cov=src --cov-report=term-missing --cov-report=html tests/

lint:
	ruff check src/ tests/
	black --check src/ tests/

security:
	pip install -e .[security]
	bandit -r src/
	safety check
	pip-audit

# Running Services
run-ui:
	streamlit run src/ui/streamlit_app.py

run-rag:
	python -m src.rag_pipeline.pipeline

run-mcp:
	python -m mcp

run-api:
	python -m src.api.main

run-agentic-rag:
	python -m src.agentic_rag.agent.agent

dev:
	streamlit run src/ui/streamlit_app.py --server.runOnSave true

# Docker
docker-build:
	docker-compose build

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

# Database (Supabase and Neo4j)
db-setup:
	echo "Using Supabase - no local database setup needed"
	echo "Configure your Supabase project and set SUPABASE_URL and SUPABASE_SERVICE_KEY"
	echo "For Neo4j, ensure NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD are set"

db-migrate:
	echo "Database migrations handled through Supabase dashboard or CLI"

neo4j-init:
	python -m src.agentic_rag.storage.neo4j_store init

ingest:
	python -m src.agentic_rag.ingestion.pipeline ingest

ingest-clean:
	python -m src.agentic_rag.ingestion.pipeline --clean

# Development utilities
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

clean-all: clean
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf build/ dist/

requirements:
	pip-compile pyproject.toml --output-file requirements.txt --resolver=backtracking

install-dev:
	python -m pip install -e .[dev]

.PHONY: setup check format test test-coverage lint security run-ui run-rag run-mcp run-api run-agentic-rag dev docker-build docker-run docker-stop db-setup db-migrate neo4j-init ingest ingest-clean clean clean-all requirements install-dev
