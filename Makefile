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

# Running Services
run-ui:
	streamlit run src/ui/streamlit_app.py

run-rag:
	python -m src.rag_pipeline.pipeline

run-mcp:
	python -m mcp

dev:
	streamlit run src/ui/streamlit_app.py --server.runOnSave true

# Docker
docker-build:
	docker-compose build

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

# Database (Supabase)
db-setup:
	echo "Using Supabase - no local database setup needed"
	echo "Configure your Supabase project and set SUPABASE_URL and SUPABASE_SERVICE_KEY"

db-migrate:
	echo "Database migrations handled through Supabase dashboard or CLI"

# Development utilities
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

install-dev:
	python -m pip install -e .[dev]

.PHONY: setup check format test test-coverage lint run-ui run-rag run-mcp dev docker-build docker-run docker-stop db-setup db-migrate clean install-dev
