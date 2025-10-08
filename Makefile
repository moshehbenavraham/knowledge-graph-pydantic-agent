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
	UI_MODE=$(or $(MODE),standard) streamlit run src/ui/streamlit_app.py

run-ui-simple:
	UI_MODE=simple streamlit run src/ui/streamlit_app.py

run-ui-advanced:
	UI_MODE=advanced streamlit run src/ui/streamlit_app.py

run-rag:
	python -m src.rag_pipeline.pipeline

run-mcp:
	python -m mcp

run-api:
	python -m src.api.main

run-agentic-rag:
	python -m src.agentic_rag.agent.agent

dev:
	UI_MODE=$(or $(MODE),standard) streamlit run src/ui/streamlit_app.py --server.runOnSave true

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

# Performance Testing
load-test:
	locust -f tests/load/locustfile.py --host=http://localhost:8058

load-test-headless:
	locust -f tests/load/locustfile.py \
		--headless \
		--users 100 \
		--spawn-rate 10 \
		--run-time 5m \
		--host=http://localhost:8058

stress-test:
	locust -f tests/load/scenarios.py \
		--headless \
		--users 200 \
		--spawn-rate 20 \
		--run-time 10m \
		--host=http://localhost:8058 \
		--html=stress-test-report.html

# Monitoring
monitoring-up:
	docker-compose -f docker-compose.monitoring.yml up -d

monitoring-down:
	docker-compose -f docker-compose.monitoring.yml down

monitoring-logs:
	docker-compose -f docker-compose.monitoring.yml logs -f

# Profiling
profile:
	py-spy record -d 30 -f flamegraph.svg -- python -m src.api.main

profile-memory:
	mprof run python -m src.api.main
	mprof plot

# Database Migrations
db-migrate:
	alembic upgrade head

db-rollback:
	alembic downgrade -1

db-history:
	alembic history

db-revision:
	alembic revision --autogenerate -m "$(msg)"

# Redis Cache
redis-cli:
	docker exec -it agentic-rag-redis redis-cli

redis-flush:
	docker exec -it agentic-rag-redis redis-cli FLUSHALL

redis-stats:
	docker exec -it agentic-rag-redis redis-cli INFO stats

redis-monitor:
	docker exec -it agentic-rag-redis redis-cli MONITOR

# API Testing
api-test:
	httpie POST localhost:8058/api/v1/chat message="Hello" session_id="test"

api-search:
	httpie POST localhost:8058/api/v1/search query="AI" search_type="hybrid"

api-metrics:
	httpie GET localhost:8058/metrics

api-status:
	httpie GET localhost:8058/api/v1/status

# Combined Operations
full-stack-up:
	docker-compose up -d
	docker-compose -f docker-compose.monitoring.yml up -d
	@echo "Waiting for services to start..."
	@sleep 10
	@echo "Stack is ready!"
	@echo "- API: http://localhost:8058"
	@echo "- Grafana: http://localhost:3000 (admin/admin)"
	@echo "- Prometheus: http://localhost:9090"
	@echo "- Jaeger: http://localhost:16686"

full-stack-down:
	docker-compose down
	docker-compose -f docker-compose.monitoring.yml down

benchmark:
	@echo "Running performance benchmark..."
	python -m pytest tests/test_performance.py -v --benchmark-only
	locust -f tests/load/locustfile.py \
		--headless \
		--users 50 \
		--spawn-rate 5 \
		--run-time 2m \
		--host=http://localhost:8058 \
		--csv=benchmark

# Poetry - Modern Dependency Management
poetry-install:
	poetry install --all-extras

poetry-update:
	poetry update

poetry-lock:
	poetry lock

poetry-export:
	poetry export -f requirements.txt --output requirements.txt --without-hashes

poetry-build:
	poetry build

poetry-shell:
	poetry shell

poetry-check:
	poetry check

poetry-show:
	poetry show --tree

# Tox - Multi-Environment Testing
tox:
	tox

tox-py311:
	tox -e py311

tox-py312:
	tox -e py312

tox-lint:
	tox -e lint

tox-security:
	tox -e security

tox-parallel:
	tox -p auto

tox-recreate:
	tox --recreate

# HTTPie - API Testing
http-test:
	@echo "Running HTTPie API tests..."
	bash tests/api_examples/httpie_examples.sh

http-chat:
	http POST localhost:8058/api/v1/chat message="$(msg)" session_id="test"

http-search:
	http POST localhost:8058/api/v1/search query="$(q)" search_type="hybrid"

http-status:
	http GET localhost:8058/api/v1/status

http-metrics:
	http GET localhost:8058/metrics

# Py-spy - Performance Profiling
profile-api:
	python scripts/profile.py api -d 30

profile-ui:
	python scripts/profile.py ui -d 30

profile-rag:
	python scripts/profile.py rag -d 30

profile-tests:
	python scripts/profile.py tests

profile-top:
	python scripts/profile.py top

profile-memory-api:
	python scripts/profile.py memory api -d 60

profile-memory-ui:
	python scripts/profile.py memory ui -d 60

# Redis Commander - Cache Management UI
redis-commander-up:
	docker-compose -f docker-compose.monitoring.yml up -d redis-commander
	@echo "Redis Commander available at http://localhost:8081"

redis-commander-down:
	docker-compose -f docker-compose.monitoring.yml stop redis-commander

redis-commander-logs:
	docker-compose -f docker-compose.monitoring.yml logs -f redis-commander

# Enhanced Development Commands
dev-setup: poetry-install pre-commit-install
	@echo "Development environment setup complete!"

dev-check: tox-lint tox-security test-coverage
	@echo "All checks passed!"

dev-format: format
	poetry run docformatter -i -r src/

dev-clean: clean-all
	rm -rf .tox/
	rm -rf poetry.lock
	poetry cache clear --all pypi

# Pre-commit hooks
pre-commit-install:
	pre-commit install
	pre-commit install --hook-type commit-msg

pre-commit-run:
	pre-commit run --all-files

# ============================================================================
# TIER 3: DOCUMENTATION & COLLABORATION TOOLS
# ============================================================================

# Sphinx Documentation
docs-sphinx-install:
	pip install -r docs_sphinx/requirements.txt

docs-sphinx-build:
	@echo "Building Sphinx documentation..."
	cd docs_sphinx && sphinx-build -b html . _build/html
	@echo "Sphinx docs built at docs_sphinx/_build/html"

docs-sphinx-serve:
	@echo "Serving Sphinx documentation at http://localhost:8000"
	cd docs_sphinx/_build/html && python -m http.server 8000

docs-sphinx-clean:
	rm -rf docs_sphinx/_build

docs-sphinx-autobuild:
	pip install sphinx-autobuild
	sphinx-autobuild docs_sphinx docs_sphinx/_build/html --port 8001

# MkDocs Documentation
docs-mkdocs-install:
	pip install mkdocs mkdocs-material mkdocstrings[python] mkdocs-mermaid2-plugin \
		mkdocs-git-revision-date-localized-plugin mkdocs-minify-plugin

docs-mkdocs-build:
	@echo "Building MkDocs documentation..."
	mkdocs build
	@echo "MkDocs built at site/"

docs-mkdocs-serve:
	@echo "Serving MkDocs at http://localhost:8002"
	mkdocs serve --dev-addr 127.0.0.1:8002

docs-mkdocs-deploy:
	@echo "Deploying MkDocs to GitHub Pages..."
	mkdocs gh-deploy --force

docs-mkdocs-clean:
	rm -rf site/

# Combined Documentation Commands
docs-install: docs-sphinx-install docs-mkdocs-install
	@echo "All documentation dependencies installed"

docs-build-all: docs-sphinx-build docs-mkdocs-build
	@echo "All documentation built successfully"

docs-serve:
	@echo "Starting documentation servers..."
	@echo "Sphinx: http://localhost:8000"
	@echo "MkDocs: http://localhost:8002"
	$(MAKE) -j 2 docs-sphinx-serve docs-mkdocs-serve

docs-clean-all: docs-sphinx-clean docs-mkdocs-clean
	@echo "All documentation cleaned"

# API Testing with Collections
api-test-postman:
	@echo "Running Postman collection tests..."
	@if command -v newman >/dev/null 2>&1; then \
		newman run api_collections/postman_collection.json \
			--environment api_collections/postman_env_dev.json \
			--reporters cli,json \
			--reporter-json-export postman_test_results.json; \
	else \
		echo "Newman not installed. Install with: npm install -g newman"; \
	fi

api-test-insomnia:
	@echo "Running Insomnia collection tests..."
	@if command -v inso >/dev/null 2>&1; then \
		inso run test api_collections/insomnia_collection.json \
			--env Development; \
	else \
		echo "Inso CLI not installed. Install with: npm install -g insomnia-inso"; \
	fi

api-import-postman:
	@echo "Import this collection into Postman:"
	@echo "File: api_collections/postman_collection.json"
	@echo "Or use the Postman API to import programmatically"

api-import-insomnia:
	@echo "Import this collection into Insomnia:"
	@echo "File: api_collections/insomnia_collection.json"

api-export-openapi:
	@echo "Exporting OpenAPI specification..."
	python -c "from src.api.main import app; import json; \
		spec = app.openapi(); \
		with open('api_collections/openapi_spec.json', 'w') as f: \
			json.dump(spec, f, indent=2)"
	@echo "OpenAPI spec exported to api_collections/openapi_spec.json"

# Mermaid Diagram Generation
diagrams-render:
	@echo "Rendering Mermaid diagrams..."
	@if command -v mmdc >/dev/null 2>&1; then \
		mmdc -i docs/architecture_diagrams.md -o docs/diagrams/; \
	else \
		echo "Mermaid CLI not installed. Install with: npm install -g @mermaid-js/mermaid-cli"; \
	fi

diagrams-preview:
	@echo "Preview Mermaid diagrams at https://mermaid.live"
	@echo "Copy diagram code from docs/architecture_diagrams.md"

# Documentation Validation
docs-validate:
	@echo "Validating documentation..."
	# Check for broken links in Sphinx docs
	cd docs_sphinx && sphinx-build -b linkcheck . _build/linkcheck
	# Validate MkDocs configuration
	mkdocs build --strict

docs-spell-check:
	@echo "Spell checking documentation..."
	@if command -v aspell >/dev/null 2>&1; then \
		find docs docs_sphinx -name "*.md" -o -name "*.rst" | \
			xargs aspell check --mode=markdown; \
	else \
		echo "Aspell not installed. Install with your package manager"; \
	fi

# Full Tier 3 Setup
tier3-setup: docs-install
	npm install -g newman insomnia-inso @mermaid-js/mermaid-cli
	@echo "Tier 3 tools setup complete!"

tier3-test: api-test-postman docs-validate
	@echo "Tier 3 tests complete!"

tier3-demo:
	@echo "Starting Tier 3 demonstration..."
	$(MAKE) docs-serve &
	sleep 2
	@echo "Documentation servers running"
	@echo "Sphinx: http://localhost:8000"
	@echo "MkDocs: http://localhost:8002"
	@echo "API Collections available in api_collections/"

pre-commit-update:
	pre-commit autoupdate

# Combined Workflows
full-test: tox-parallel benchmark
	@echo "Full test suite completed!"

full-profile: profile-api profile-ui profile-rag
	@echo "Profiling complete. Check generated flamegraphs."

full-monitoring: monitoring-up redis-commander-up
	@echo "Full monitoring stack is up!"
	@echo "- Prometheus: http://localhost:9090"
	@echo "- Grafana: http://localhost:3000"
	@echo "- Jaeger: http://localhost:16686"
	@echo "- Redis Commander: http://localhost:8081"

.PHONY: setup check format test test-coverage lint security run-ui run-rag run-mcp run-api run-agentic-rag dev docker-build docker-run docker-stop db-setup db-migrate neo4j-init ingest ingest-clean clean clean-all requirements install-dev load-test load-test-headless stress-test monitoring-up monitoring-down monitoring-logs profile profile-memory db-migrate db-rollback db-history db-revision redis-cli redis-flush redis-stats redis-monitor api-test api-search api-metrics api-status full-stack-up full-stack-down benchmark poetry-install poetry-update poetry-lock poetry-export poetry-build poetry-shell poetry-check poetry-show tox tox-py311 tox-py312 tox-lint tox-security tox-parallel tox-recreate http-test http-chat http-search http-status http-metrics profile-api profile-ui profile-rag profile-tests profile-top profile-memory-api profile-memory-ui redis-commander-up redis-commander-down redis-commander-logs dev-setup dev-check dev-format dev-clean pre-commit-install pre-commit-run pre-commit-update full-test full-profile full-monitoring
