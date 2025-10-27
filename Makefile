# Core Development
setup:
	python -m pip install -e .[dev]
	pre-commit install

check:
	bash -c "source .venv/bin/activate && ruff check src/ tests/"
	bash -c "source .venv/bin/activate && mypy src/ tests/"
	bash -c "source .venv/bin/activate && pytest tests/"

format:
	bash -c "source .venv/bin/activate && black src/ tests/"
	bash -c "source .venv/bin/activate && ruff check --fix src/ tests/"

test:  ## Run test suite (1,113 tests, ~7-10 minutes)
	bash -c "source .venv/bin/activate && pytest tests/"

test-coverage:  ## Run tests with coverage (1,113 tests, ~10-15 minutes) - USE GENEROUS TIMEOUTS IN SCRIPTS
	bash -c "source .venv/bin/activate && pytest --cov=src --cov-report=term-missing --cov-report=html tests/"

lint:
	bash -c "source .venv/bin/activate && ruff check src/ tests/"
	bash -c "source .venv/bin/activate && black --check src/ tests/"

security:
	bash -c "source .venv/bin/activate && pip install -e .[security]"
	bash -c "source .venv/bin/activate && bandit -r src/"
	bash -c "source .venv/bin/activate && safety check"
	bash -c "source .venv/bin/activate && pip-audit"

# Code Quality Analysis
deadcode:
	@echo "🔍 Scanning for dead code..."
	bash -c "source .venv/bin/activate && vulture src/ tests/ --min-confidence 70"

complexity:
	@echo "📊 Analyzing code complexity..."
	@echo "\n=== Cyclomatic Complexity ==="
	bash -c "source .venv/bin/activate && radon cc src/ -a -nb"
	@echo "\n=== Maintainability Index ==="
	bash -c "source .venv/bin/activate && radon mi src/ -nb"

docstring-coverage:
	@echo "📝 Checking docstring coverage..."
	bash -c "source .venv/bin/activate && interrogate src/ -v --fail-under 75 --ignore-init-method --ignore-init-module"

# Comprehensive quality check
quality: lint security deadcode complexity docstring-coverage
	@echo "✅ All quality checks passed!"

# Running Services
run-ui:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=$(or $(MODE),advanced) streamlit run src/ui/streamlit_app.py"

run-ui-simple:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=simple streamlit run src/ui/streamlit_app.py"

run-ui-standard:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=standard streamlit run src/ui/streamlit_app.py"

run-ui-advanced:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=advanced streamlit run src/ui/streamlit_app.py"

run-rag:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH python -m src.rag_pipeline.pipeline"

run-mcp:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH python -m mcp"

run-api:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH python -m src.api.main"

run-agentic-rag:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH python -m src.agentic_rag.agent.agent"

dev:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=$(or $(MODE),advanced) streamlit run src/ui/streamlit_app.py --server.runOnSave true"

# ngrok Deployment
ngrok-start:  ## Start ngrok tunnel manually
	ngrok start base-agent-ui

ngrok-ui:  ## Start Streamlit only (for manual ngrok)
	bash -c "source .venv/bin/activate && \
	  PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=advanced \
	  streamlit run src/ui/streamlit_app.py --server.port=8501"

deploy-ngrok:  ## Start Streamlit + ngrok tunnel + HTTP log monitor (logs to logs/ngrok_auth_logs/)
	@mkdir -p logs/ngrok_auth_logs
	@echo "Cleaning up logs older than 3 days..."
	@find logs/ngrok_auth_logs -name "*.log" -type f -mtime +3 -delete 2>/dev/null || true
	@echo "Starting Streamlit on port 8501..."
	@bash -c "source .venv/bin/activate && \
	  PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=advanced \
	  streamlit run src/ui/streamlit_app.py --server.port=8501 2>&1 | tee logs/ngrok_auth_logs/streamlit_$$(date +%Y%m%d_%H%M%S).log" & \
	sleep 5 && \
	echo "Starting ngrok tunnel to aiwithapex.ngrok.io..." && \
	ngrok start base-agent-ui 2>&1 | tee logs/ngrok_auth_logs/ngrok_$$(date +%Y%m%d_%H%M%S).log & \
	sleep 3 && \
	echo "Starting ngrok HTTP log monitor..." && \
	bash -c "source .venv/bin/activate && python3 scripts/monitor_ngrok_logs.py"

ngrok-status:  ## Check ngrok tunnel status
	@curl -s http://localhost:4040/api/tunnels | python -m json.tool

ngrok-logs:  ## View ngrok access logs (via API)
	@curl -s http://localhost:4040/api/requests/http | python -m json.tool

ngrok-monitor:  ## Start ngrok HTTP log monitor (writes to logs/ngrok_auth_logs/)
	@bash -c "source .venv/bin/activate && python3 scripts/monitor_ngrok_logs.py"

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

# db-migrate is defined later in the file (line 141)

neo4j-init:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH python -m src.agentic_rag.storage.neo4j_store init"

ingest:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH python -m src.agentic_rag.ingestion.pipeline ingest"

ingest-clean:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH python -m src.agentic_rag.ingestion.pipeline --clean"

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

# ============================================================================
# PHASE 5: PRODUCTION DEPLOYMENT & OPERATIONS
# ============================================================================

# Registry and Image Configuration
REGISTRY ?= ghcr.io/aiwithapex
IMAGE_NAME ?= base-agent
IMAGE_TAG ?= $(shell git rev-parse --short HEAD)
IMAGE_FULL = $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

# ===== Container Image Build & Management =====

image-build:
	@echo "Building production image: $(IMAGE_FULL)"
	docker build \
		-f docker/Dockerfile.production \
		-t $(IMAGE_NAME):latest \
		-t $(IMAGE_NAME):$(IMAGE_TAG) \
		-t $(IMAGE_FULL) \
		--build-arg BUILD_DATE=$(shell date -u +'%Y-%m-%dT%H:%M:%SZ') \
		--build-arg VCS_REF=$(shell git rev-parse HEAD) \
		--target runtime \
		.

image-build-api:
	@echo "Building API server image: $(IMAGE_FULL)-api"
	docker build \
		-f docker/Dockerfile.production \
		-t $(IMAGE_NAME)-api:latest \
		-t $(IMAGE_NAME)-api:$(IMAGE_TAG) \
		-t $(REGISTRY)/$(IMAGE_NAME)-api:$(IMAGE_TAG) \
		--target api \
		.

image-push:
	@echo "Pushing image to registry: $(IMAGE_FULL)"
	docker push $(IMAGE_FULL)
	docker push $(REGISTRY)/$(IMAGE_NAME):latest

image-push-api:
	@echo "Pushing API image to registry"
	docker push $(REGISTRY)/$(IMAGE_NAME)-api:$(IMAGE_TAG)
	docker push $(REGISTRY)/$(IMAGE_NAME)-api:latest

image-tag-release:
	@echo "Tagging release version $(VERSION)"
	docker tag $(IMAGE_NAME):latest $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
	docker push $(REGISTRY)/$(IMAGE_NAME):$(VERSION)

# ===== Security Scanning & SBOM =====

image-scan:
	@echo "Scanning image for vulnerabilities with Trivy..."
	trivy image --severity HIGH,CRITICAL --exit-code 1 $(IMAGE_NAME):latest

image-scan-full:
	@echo "Full vulnerability scan (all severities)..."
	trivy image \
		--severity CRITICAL,HIGH,MEDIUM,LOW \
		--format json \
		--output trivy-report.json \
		$(IMAGE_NAME):latest
	@echo "Scan report saved to trivy-report.json"

image-sbom:
	@echo "Generating SBOM with Syft..."
	syft packages $(IMAGE_NAME):latest -o spdx-json > sbom.spdx.json
	syft packages $(IMAGE_NAME):latest -o cyclonedx-json > sbom.cyclonedx.json
	@echo "SBOM generated: sbom.spdx.json, sbom.cyclonedx.json"

image-sign:
	@echo "Signing image with Cosign..."
	cosign sign --yes $(IMAGE_FULL)

image-verify:
	@echo "Verifying image signature..."
	cosign verify --key cosign.pub $(IMAGE_FULL)

# ===== Environment-Specific Deployments =====

deploy-dev:
	@echo "Deploying to DEV environment..."
	docker-compose -f docker/docker-compose.dev.yml up -d
	@echo "DEV environment running"

deploy-dev-down:
	docker-compose -f docker/docker-compose.dev.yml down

deploy-staging:
	@echo "Deploying to STAGING environment..."
	export REGISTRY=$(REGISTRY) && \
	export IMAGE_TAG=$(IMAGE_TAG) && \
	docker-compose -f docker/docker-compose.staging.yml up -d
	@echo "STAGING environment running"

deploy-staging-down:
	docker-compose -f docker/docker-compose.staging.yml down

deploy-prod:
	@echo "Deploying to PRODUCTION environment..."
	@echo "WARNING: This will deploy to production. Continue? [y/N]"
	@read confirm && [ "$$confirm" = "y" ] || exit 1
	export REGISTRY=$(REGISTRY) && \
	export IMAGE_TAG=$(IMAGE_TAG) && \
	bash deploy/scripts/deploy.sh production
	@echo "PRODUCTION deployment initiated"

deploy-prod-down:
	docker-compose -f docker/docker-compose.prod.yml down

# ===== Health Checks & Validation =====

health-check:
	@echo "Checking service health..."
	@curl -f http://localhost:8501/_stcore/health || echo "UI health check failed"
	@curl -f http://localhost:8058/health || echo "API health check failed"

health-check-staging:
	@echo "Checking STAGING health..."
	bash deploy/scripts/health-check.sh staging

health-check-prod:
	@echo "Checking PRODUCTION health..."
	bash deploy/scripts/health-check.sh production

# ===== Rollback & Recovery =====

rollback-staging:
	@echo "Rolling back STAGING to previous version..."
	bash deploy/scripts/rollback.sh staging

rollback-prod:
	@echo "Rolling back PRODUCTION to previous version..."
	@echo "WARNING: This will rollback production. Continue? [y/N]"
	@read confirm && [ "$$confirm" = "y" ] || exit 1
	bash deploy/scripts/rollback.sh production

# ===== Full Supply Chain Workflow =====

ci-supply-chain: image-build image-scan image-sbom
	@echo "Supply chain security checks complete"

ci-deploy: ci-supply-chain image-sign image-push
	@echo "CI deployment pipeline complete"

# ===== Monitoring & Observability =====

logs-app:
	docker logs -f base-agent-prod

logs-api:
	docker logs -f base-agent-api-prod

logs-all:
	docker-compose -f docker/docker-compose.prod.yml logs -f

metrics-export:
	@echo "Exporting metrics..."
	curl http://localhost:8000/metrics > metrics-export.txt
	@echo "Metrics saved to metrics-export.txt"

# ===== Cleanup =====

image-clean:
	@echo "Cleaning up old images..."
	docker image prune -a -f --filter "until=168h"

deploy-clean-all:
	docker-compose -f docker/docker-compose.dev.yml down -v
	docker-compose -f docker/docker-compose.staging.yml down -v
	docker-compose -f docker/docker-compose.prod.yml down -v

.PHONY: setup check format test test-coverage lint security run-ui run-ui-simple run-ui-standard run-ui-advanced run-rag run-mcp run-api run-agentic-rag dev ngrok-start ngrok-ui deploy-ngrok ngrok-status ngrok-logs docker-build docker-run docker-stop db-setup db-migrate neo4j-init ingest ingest-clean clean clean-all requirements install-dev load-test load-test-headless stress-test monitoring-up monitoring-down monitoring-logs profile profile-memory db-migrate db-rollback db-history db-revision redis-cli redis-flush redis-stats redis-monitor api-test api-search api-metrics api-status full-stack-up full-stack-down benchmark poetry-install poetry-update poetry-lock poetry-export poetry-build poetry-shell poetry-check poetry-show tox tox-py311 tox-py312 tox-lint tox-security tox-parallel tox-recreate http-test http-chat http-search http-status http-metrics profile-api profile-ui profile-rag profile-tests profile-top profile-memory-api profile-memory-ui redis-commander-up redis-commander-down redis-commander-logs dev-setup dev-check dev-format dev-clean pre-commit-install pre-commit-run pre-commit-update full-test full-profile full-monitoring image-build image-build-api image-push image-push-api image-tag-release image-scan image-scan-full image-sbom image-sign image-verify deploy-dev deploy-dev-down deploy-staging deploy-staging-down deploy-prod deploy-prod-down health-check health-check-staging health-check-prod rollback-staging rollback-prod ci-supply-chain ci-deploy logs-app logs-api logs-all metrics-export image-clean deploy-clean-all
