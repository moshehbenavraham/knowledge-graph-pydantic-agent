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

test:  ## Run test suite (3,788 tests, ~7-10 minutes)
	bash -c "source .venv/bin/activate && pytest tests/"

test-coverage:  ## Run tests with coverage (3,788 tests, ~10-15 minutes) - USE GENEROUS TIMEOUTS IN SCRIPTS
	bash -c "source .venv/bin/activate && pytest --cov=src --cov-report=term-missing --cov-report=html tests/"

test-parallel:  ## Run tests in parallel using pytest-xdist (faster, ~2-5 minutes)
	bash -c "source .venv/bin/activate && pytest tests/ -n auto"

test-parallel-coverage:  ## Run tests in parallel with coverage (~5-8 minutes)
	bash -c "source .venv/bin/activate && pytest tests/ -n auto --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=75"

test-durations:  ## Show 20 slowest tests
	bash -c "source .venv/bin/activate && pytest tests/ --durations=20 -q"

lint:
	bash -c "source .venv/bin/activate && ruff check src/ tests/"
	bash -c "source .venv/bin/activate && black --check src/ tests/"
	bash -c "source .venv/bin/activate && mypy src/ tests/"

security:
	bash -c "source .venv/bin/activate && pip install -e .[security]"
	bash -c "source .venv/bin/activate && bandit -r src/"
	bash -c "source .venv/bin/activate && safety scan"
	bash -c "source .venv/bin/activate && pip-audit --ignore-vuln PYSEC-2023-242 --ignore-vuln PYSEC-2022-42969"

# Note: Ignored vulnerabilities above are documented in pyproject.toml and .pip-audit.toml:
# - PYSEC-2023-242: httpie SSL cert validation in update check - no fix available, dev-only tool
# - PYSEC-2022-42969: py library ReDoS in SVN handling - disputed, SVN-only, dev-only (via interrogate)

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
	@lsof -ti :8502 | xargs kill -9 2>/dev/null || true
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=$(or $(MODE),advanced) streamlit run src/ui/streamlit_app.py --server.port=8502"

run-ui-simple:
	@lsof -ti :8502 | xargs kill -9 2>/dev/null || true
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=simple streamlit run src/ui/streamlit_app.py --server.port=8502"

run-ui-standard:
	@lsof -ti :8502 | xargs kill -9 2>/dev/null || true
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=standard streamlit run src/ui/streamlit_app.py --server.port=8502"

run-ui-advanced:
	@lsof -ti :8502 | xargs kill -9 2>/dev/null || true
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=advanced streamlit run src/ui/streamlit_app.py --server.port=8502"

run-rag:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH python -m src.rag_pipeline.pipeline"

run-mcp:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH python -m mcp"

run-api:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH python -m src.api.main"

run-agentic-rag:
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH python -m src.agentic_rag.agent.agent"

dev:
	@lsof -ti :8502 | xargs kill -9 2>/dev/null || true
	bash -c "source .venv/bin/activate && PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=$(or $(MODE),advanced) streamlit run src/ui/streamlit_app.py --server.port=8502 --server.runOnSave true"

# ngrok Deployment
ngrok-start:  ## Start ngrok tunnel manually (foreground)
	ngrok start base-agent-ui

ngrok-ui:  ## Start Streamlit only (foreground, for manual ngrok)
	@lsof -ti :8502 | xargs kill -9 2>/dev/null || true
	bash -c "source .venv/bin/activate && \
	  PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=advanced \
	  streamlit run src/ui/streamlit_app.py --server.port=8502"

deploy-ngrok:  ## Start Streamlit + ngrok (background, persistent) - use deploy-ngrok-stop to stop
	@echo "Stopping any existing services..."
	@lsof -ti :8502 | xargs kill -9 2>/dev/null || true
	@lsof -ti :4040 | xargs kill -9 2>/dev/null || true
	@killall ngrok 2>/dev/null || true
	@sleep 2
	@mkdir -p logs
	@echo "Starting Streamlit on port 8502..."
	@bash -c "source .venv/bin/activate && \
	  PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=advanced \
	  nohup streamlit run src/ui/streamlit_app.py --server.port=8502 > logs/streamlit.log 2>&1 &"
	@sleep 4
	@echo "Starting ngrok tunnel..."
	@bash -c "nohup ngrok start base-agent-ui > logs/ngrok.log 2>&1 &"
	@sleep 4
	@echo ""
	@echo "=============================================="
	@echo "  DEPLOYMENT COMPLETE"
	@echo "=============================================="
	@echo ""
	@echo "Local:  http://localhost:8502"
	@curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('Public: ' + d['tunnels'][0]['public_url'])" 2>/dev/null || echo "Public: (ngrok starting...check with 'make ngrok-status')"
	@echo ""
	@echo "Logs:   logs/streamlit.log, logs/ngrok.log"
	@echo "Stop:   make deploy-ngrok-stop"
	@echo "=============================================="

deploy-ngrok-stop:  ## Stop Streamlit + ngrok services
	@echo "Stopping services..."
	@lsof -ti :8502 | xargs kill -9 2>/dev/null || true
	@lsof -ti :4040 | xargs kill -9 2>/dev/null || true
	@killall ngrok 2>/dev/null || true
	@killall streamlit 2>/dev/null || true
	@echo "Services stopped."

deploy-ngrok-restart:  ## Restart Streamlit + ngrok services
	@$(MAKE) deploy-ngrok-stop
	@sleep 2
	@$(MAKE) deploy-ngrok

ngrok-status:  ## Check ngrok tunnel status and URL
	@echo "Checking ngrok status..."
	@curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); t=d.get('tunnels',[]); print('Tunnel: ' + t[0]['public_url'] if t else 'No active tunnels')" 2>/dev/null || echo "ngrok API not responding (is ngrok running?)"
	@echo ""
	@echo "Streamlit: $$(lsof -ti :8502 >/dev/null 2>&1 && echo 'Running' || echo 'Not running')"
	@echo "ngrok:     $$(pgrep -f 'ngrok start' >/dev/null 2>&1 && echo 'Running' || echo 'Not running')"

ngrok-logs:  ## View ngrok access logs (via API)
	@curl -s http://localhost:4040/api/requests/http | python3 -m json.tool

ngrok-monitor:  ## Start ngrok HTTP log monitor (foreground, writes to logs/ngrok_auth_logs/)
	@mkdir -p logs/ngrok_auth_logs
	@bash -c "source .venv/bin/activate && python3 scripts/monitor_ngrok_logs.py"

# Coolify Deployment
coolify-check:  ## Run pre-deployment checks for Coolify
	@echo "Running Coolify pre-deployment checks..."
	@bash scripts/coolify-pre-deploy-check.sh

coolify-env:  ## Generate Coolify environment variables template
	@echo "Generating Coolify environment template..."
	@bash scripts/generate-coolify-env.sh

coolify-build:  ## Build production Docker image for Coolify
	@echo "Building Coolify production image..."
	docker build \
		-f docker/Dockerfile.production \
		-t base-agent:latest \
		--target runtime \
		.

coolify-test-build:  ## Test build Coolify Docker image locally
	@echo "Testing Coolify Docker build..."
	docker build \
		-f docker/Dockerfile.production \
		-t base-agent:coolify-test \
		--target runtime \
		. && \
	echo "Build successful! Test with: docker run -p 8502:8502 --env-file .env base-agent:coolify-test"

coolify-compose-up:  ## Start services using Coolify docker-compose (local test)
	@echo "Starting Coolify services locally..."
	docker-compose -f docker/docker-compose.coolify.yml up -d

coolify-compose-down:  ## Stop Coolify docker-compose services
	docker-compose -f docker/docker-compose.coolify.yml down

coolify-compose-logs:  ## View logs from Coolify docker-compose
	docker-compose -f docker/docker-compose.coolify.yml logs -f

coolify-deploy-api:  ## Deploy to Coolify via API (fully automated)
	@echo "Deploying to Coolify via API..."
	@bash scripts/coolify-deploy.sh

# Docker
docker-build:
	docker-compose -f docker/docker-compose.yml build

docker-run:
	docker-compose -f docker/docker-compose.yml up -d

docker-stop:
	docker-compose -f docker/docker-compose.yml down

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

# Monitoring (use Coolify or external monitoring)
# monitoring-up, monitoring-down, monitoring-logs removed - use external monitoring

# Profiling
profile:
	py-spy record -d 30 -f flamegraph.svg -- python -m src.api.main

profile-memory:
	mprof run python -m src.api.main
	mprof plot

# Database Migrations (use SQL files in src/agentic_rag/storage/migrations/sql/)
# Alembic removed - apply SQL migrations directly to Supabase

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
	docker-compose -f docker/docker-compose.yml up -d
	@echo "Waiting for services to start..."
	@sleep 10
	@echo "Stack is ready!"
	@echo "- UI: http://localhost:8502"
	@echo "- API: http://localhost:8058"

full-stack-down:
	docker-compose -f docker/docker-compose.yml down

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

# Multi-Environment Testing (tox removed - use make test directly)

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

# Redis Commander removed - use external Redis management tools

# Enhanced Development Commands
dev-setup: poetry-install pre-commit-install
	@echo "Development environment setup complete!"

dev-check: lint security test-coverage
	@echo "All checks passed!"

dev-format: format
	poetry run docformatter -i -r src/

dev-clean: clean-all
	rm -rf poetry.lock
	poetry cache clear --all pypi

# Pre-commit hooks
pre-commit-install:
	pre-commit install
	pre-commit install --hook-type commit-msg

pre-commit-run:
	pre-commit run --all-files

# Documentation is in docs/ folder - no build system needed

pre-commit-update:
	pre-commit autoupdate

# Combined Workflows
full-test: test-parallel benchmark
	@echo "Full test suite completed!"

full-profile: profile-api profile-ui profile-rag
	@echo "Profiling complete. Check generated flamegraphs."

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
	@echo "Use Coolify dashboard for production deployments"
	@echo "Or run: docker-compose -f docker/docker-compose.prod.yml up -d"

deploy-prod-down:
	docker-compose -f docker/docker-compose.prod.yml down

# ===== Health Checks & Validation =====

health-check:
	@echo "Checking service health..."
	@curl -f http://localhost:8502/_stcore/health || echo "UI health check failed"
	@curl -f http://localhost:8058/health || echo "API health check failed"

health-check-staging:
	@echo "Checking STAGING health..."
	@curl -f http://localhost:8502/_stcore/health || echo "Health check failed"

health-check-prod:
	@echo "Checking PRODUCTION health..."
	@echo "Check Coolify dashboard for production health status"

# ===== Rollback & Recovery =====
# Use Coolify dashboard for rollback operations

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
	curl http://localhost:8002/metrics > metrics-export.txt
	@echo "Metrics saved to metrics-export.txt"

# ===== Cleanup =====

image-clean:
	@echo "Cleaning up old images..."
	docker image prune -a -f --filter "until=168h"

deploy-clean-all:
	docker-compose -f docker/docker-compose.dev.yml down -v
	docker-compose -f docker/docker-compose.staging.yml down -v
	docker-compose -f docker/docker-compose.prod.yml down -v

.PHONY: setup check format test test-coverage lint security run-ui run-ui-simple run-ui-standard run-ui-advanced run-rag run-mcp run-api run-agentic-rag dev ngrok-start ngrok-ui deploy-ngrok deploy-ngrok-stop deploy-ngrok-restart ngrok-status ngrok-logs ngrok-monitor coolify-check coolify-env coolify-build coolify-test-build coolify-compose-up coolify-compose-down coolify-compose-logs docker-build docker-run docker-stop db-setup neo4j-init ingest ingest-clean clean clean-all requirements install-dev load-test load-test-headless stress-test profile profile-memory redis-cli redis-flush redis-stats redis-monitor api-test api-search api-metrics api-status full-stack-up full-stack-down benchmark poetry-install poetry-update poetry-lock poetry-export poetry-build poetry-shell poetry-check poetry-show http-test http-chat http-search http-status http-metrics profile-api profile-ui profile-rag profile-tests profile-top profile-memory-api profile-memory-ui dev-setup dev-check dev-format dev-clean pre-commit-install pre-commit-run pre-commit-update full-test full-profile image-build image-build-api image-push image-push-api image-tag-release image-scan image-scan-full image-sbom image-sign image-verify deploy-dev deploy-dev-down deploy-staging deploy-staging-down deploy-prod deploy-prod-down health-check health-check-staging health-check-prod ci-supply-chain ci-deploy logs-app logs-api logs-all metrics-export image-clean deploy-clean-all
