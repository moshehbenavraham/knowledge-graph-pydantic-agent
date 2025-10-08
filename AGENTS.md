# Repository Guidelines

## Project Structure & Module Organization
Runtime code lives in `src/`, with key modules for the unified agent (`src/agent`), retrieval pipeline (`src/rag_pipeline`), Streamlit UI (`src/ui`), and integrations (`src/tools`, `src/clients`, `src/api`). Test suites sit in `tests/`, mirroring the runtime layout; load and integration scenarios are under `tests/load` and `tests/api_examples`. Configuration assets are tracked in `docs/`, `docs_sphinx/`, and environment templates such as `.env.example`, while deployment and infrastructure scaffolding lives in `docker/`, `supabase/`, and `sql/`.

## Build, Test, and Development Commands
- `make setup` installs the project in editable mode with development extras and sets up pre-commit hooks.
- `make run-ui`, `make run-ui-simple`, and `make run-ui-advanced` launch the Streamlit interface with the desired feature set; `make dev` enables auto-reload.
- `make run-api` starts the FastAPI service, and `make run-rag` or `make run-agentic-rag` executes the retrieval pipelines for CLI validation.
- `make check` runs linting, type checks, and the full test suite; `make test-coverage` enforces coverage and renders `htmlcov/`.

## Coding Style & Naming Conventions
Target Python 3.11+, four-space indentation, and a 100-character line limit (enforced by Black and Ruff). Favor snake_case for modules and functions, PascalCase for classes, and maintain descriptive Pydantic model names. Ruff handles linting with pycodestyle, pyflakes, bugbear, and pyupgrade rules; Black performs formatting, and `mypy` supplies optional static checks. Avoid introducing new global state—prefer dependency-injected helpers mirroring existing factories in `src/utils` and `src/config`.

## Testing Guidelines
Tests use `pytest` with async support; coverage thresholds are configured at 75% via `pyproject.toml`. Place unit tests alongside the relevant module namespace (e.g., `tests/test_config.py` for `src/config`). Name files `test_*.py`, classes `Test*`, and functions `test_*` to keep discovery reliable. Use fixtures from `tests/conftest.py` when interacting with Supabase or mock clients, and run `make test` (or `pytest -k <pattern>`) before submitting pull requests.

## Commit & Pull Request Guidelines
The history is trending toward Conventional Commits (`feat:`, `refactor:`, `fix:`), so follow that style and keep subject lines under 72 characters. Reference issue IDs or project milestones where possible, and combine related changes into a single commit. For pull requests, include: purpose summary, testing evidence (command output or screenshots for UI updates), configuration or migration notes, and any follow-up tasks. Draft PRs are encouraged while work is in progress; convert to ready status only after CI passes locally.

## Security & Configuration Tips
Secrets are injected via environment variables—copy `.env.example` to `.env` and configure Supabase, Neo4j, and LLM credentials before running services. Never commit `.env` or generated credentials; add new secrets to documentation in `docs/CONFIGURATION.md` instead. When debugging remote tooling, use the sandboxed code execution helpers rather than expanding system privileges, and sanitize logs that may contain user prompts or retrieved documents.
