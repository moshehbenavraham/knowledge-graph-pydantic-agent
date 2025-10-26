# Luminari Agent Constitution

<!--
=============================================================================
SYNC IMPACT REPORT - Constitution Update
=============================================================================
Version Change: INITIAL → 1.0.0
Date: 2025-10-21

PRINCIPLES ESTABLISHED:
- I. Unified Agent Architecture (NEW)
- II. Type-Safe Centralized Configuration (NEW)
- III. Dual-Database Agentic RAG (NEW)
- IV. Test-Driven Quality Assurance (NEW)
- V. Production-Ready Observability (NEW)
- VI. Git Attribution & Contribution Standards (NEW)

SECTIONS ADDED:
- Core Principles (6 principles)
- Development Standards
- Code Quality Gates
- Governance

TEMPLATES REQUIRING UPDATES:
✅ plan-template.md - Constitution Check section already references constitution file
✅ spec-template.md - No constitution-specific constraints to add
✅ tasks-template.md - Task categorization aligns with principles
⚠ No command files found in .specify/templates/commands/

FOLLOW-UP ITEMS:
- None - all placeholders filled with concrete values

RATIONALE FOR VERSION 1.0.0:
- Initial constitution establishing foundational governance
- All six core principles defined with clear rationale
- Development standards, quality gates, and governance rules established
- MAJOR version as this is the first ratified constitution
=============================================================================
-->

## Core Principles

### I. Unified Agent Architecture

**The repository MUST maintain exactly ONE agent implementation.**

- Single agent located at `src/agent/unified_agent.py`
- All tool integrations go through the unified agent
- Tool additions use `@super_agent.tool` decorator pattern
- NO separate agent files or implementations permitted
- Agent uses dependency injection via `UnifiedAgentDeps`

**Rationale:** Multiple agent implementations create maintenance burden, inconsistent
behavior, and configuration drift. The unified architecture ensures all features share
the same tool orchestration, memory management, and observability infrastructure.

### II. Type-Safe Centralized Configuration

**ALL configuration MUST use the centralized Pydantic settings system.**

- Configuration lives in `src/config/settings.py` as single source of truth
- Module-specific facades in `src/config/` (agent, api, clients, ui)
- ALL settings load from `.env` with automatic validation
- NEVER use `os.getenv()` directly in application code
- Use `get_settings()` or module facades (`agent_config`, `api_config`)
- All 68 configuration fields have types, defaults, and validation

**Rationale:** Centralized configuration with type safety prevents runtime errors from
invalid settings, provides clear documentation of all options, and enables validation
at startup rather than discovering issues during operation.

### III. Dual-Database Agentic RAG

**The system REQUIRES both PostgreSQL/Supabase AND Neo4j for full functionality.**

- PostgreSQL/Supabase: Vector embeddings (pgvector), document content, analytics
- Neo4j + Graphiti: Knowledge graph (entities, relationships, temporal facts)
- Both databases work together for hybrid search strategies
- Graph component is NOT optional for production deployments
- Missing graph disables: entity extraction, relationship discovery, temporal reasoning,
  graph-based search, hybrid search capabilities

**Rationale:** This is an Agentic Graph RAG system, not basic vector search. The
knowledge graph enables relationship discovery, temporal reasoning, and graph-boosted
search that vector embeddings alone cannot provide. Both components are architected
as foundational infrastructure.

### IV. Test-Driven Quality Assurance

**Testing discipline is mandatory with enforced coverage minimums.**

- Minimum 75% test coverage enforced by pytest-cov
- Pre-commit hooks run Black, Ruff, and validation automatically
- Unit tests with mocked dependencies in `tests/unit/`
- Integration tests against live databases in `tests/integration/`
- Load tests with SLO validation in `tests/load/`
- `make check` MUST pass before any PR merge
- Type hints required for all function signatures

**Rationale:** High test coverage and automated quality checks catch regressions early,
document expected behavior, enable confident refactoring, and maintain production
stability. The 75% threshold balances thoroughness with pragmatism.

### V. Production-Ready Observability

**Comprehensive observability infrastructure is mandatory, not optional.**

- Application Logging: Structured logging (structlog) across UI and agent pipeline
  with real-time execution tracking, event counters, and debug filtering
- Analytics System: Persistent event logging to PostgreSQL with search metrics, tool
  usage, agent interactions, and materialized views for dashboard queries
- Metrics: Prometheus exposition at `/metrics` for API usage, latency, cache hits
- Tracing: Optional OpenTelemetry + Jaeger integration via `ENABLE_TRACING`
- Resilience: Circuit breakers, retry logic, rate limiting, graceful degradation
- Performance tracking: Query latency, cache hit rates, connection pool stats

**Rationale:** Production systems require visibility into operations, performance, and
errors. The observability stack enables debugging, performance optimization, capacity
planning, and incident response without code changes.

### VI. Git Attribution & Contribution Standards

**All commits, code, and work MUST be attributed to the repository owner ONLY.**

- ❌ NEVER use "Co-Authored-By: Claude <noreply@anthropic.com>"
- ❌ NEVER include "Generated with Claude Code" or AI attribution
- ❌ NEVER mention Anthropic or Claude in commit messages
- ✅ Attribute all work to the repository owner (the person paying for the service)
- ✅ Use Conventional Commits format (feat:, fix:, docs:, etc.)
- ✅ Write clear, professional commit messages describing what changed and why

**Rationale:** The repository owner commissions and owns the work. AI tools are
utilities like IDEs or linters - we don't attribute code to VSCode. Professional
commit history reflects actual authorship and responsibility.

## Development Standards

### Code Style & Formatting

- **Line length:** 100 characters (Black formatter)
- **Python version:** 3.11+ required (tested with 3.11 and 3.12)
- **Type hints:** Required for all public function signatures
- **Docstrings:** Google style for all public functions and classes
- **Imports:** Organized by Ruff (stdlib → third-party → local)
- **Async patterns:** Use `async`/`await` for all I/O operations
- **Pre-commit hooks:** Enforce Black, Ruff, trailing whitespace, YAML/TOML validation

### Tool Development Patterns

All tools in `src/tools/` MUST follow these patterns:

- Async function signatures accepting `RunContext[UnifiedAgentDeps]`
- Comprehensive error handling with informative error messages
- Security validation for all inputs (especially SQL/code execution)
- Clear docstrings with Args, Returns, and usage examples
- Register with unified agent via `super_agent.tool(function_name)`

### File Organization

- New features extend existing modules rather than creating parallel structures
- UI features go in `src/ui/features/` as handlers, not new UI files
- Configuration additions go in `src/config/settings.py` with `.env.example` updates
- Database migrations use sequential numbering in `src/agentic_rag/storage/migrations/sql/`

## Code Quality Gates

### Pre-Commit Requirements

The following MUST pass before any commit is accepted:

1. **Formatting:** Black auto-format with 100-character line length
2. **Linting:** Ruff checks with zero violations
3. **Validation:** YAML and TOML syntax validation
4. **Whitespace:** No trailing whitespace

Run `make format` to auto-fix most issues.

### Pre-PR Requirements

The following MUST pass before any pull request can merge:

1. **All quality checks:** `make check` passes (lint + test + security)
2. **Test coverage:** Minimum 75% overall coverage maintained
3. **Security scan:** Bandit, Safety, and pip-audit pass with no critical issues
4. **Type checking:** MyPy passes where configured
5. **Documentation:** README and relevant docs updated for new features
6. **Commit format:** Conventional Commits used for all commits

### Testing Requirements

- **Unit tests:** Required for all new functions and classes
- **Integration tests:** Required for database operations and API endpoints
- **Load tests:** Required for performance-critical endpoints
- **Async tests:** Use `@pytest.mark.asyncio(loop_scope="module")` for database tests
- **Fixtures:** Prefer module-scoped fixtures for expensive setup (database pools)
- **Mocking:** Mock external services (LLM APIs, web search) in unit tests

## Governance

### Constitution Authority

This constitution supersedes all other practices and conventions. When conflict arises
between this document and other guidance, the constitution takes precedence.

### Amendment Procedure

1. **Proposal:** Create GitHub issue describing proposed amendment with rationale
2. **Discussion:** Allow minimum 48 hours for community feedback
3. **Documentation:** Update constitution with specific changes
4. **Version bump:** Increment version following semantic versioning:
   - **MAJOR:** Backward incompatible governance or principle removals/redefinitions
   - **MINOR:** New principles added or materially expanded guidance
   - **PATCH:** Clarifications, wording fixes, non-semantic refinements
5. **Propagation:** Update all dependent templates and documentation
6. **Approval:** Require explicit approval from repository owner
7. **Migration:** Provide migration plan if changes affect existing code

### Compliance Review

All pull requests MUST verify compliance with this constitution:

- Architecture changes reviewed against Principle I (Unified Agent)
- Configuration changes follow Principle II (Centralized Settings)
- Database changes maintain Principle III (Dual-Database RAG)
- Test coverage meets Principle IV (75% minimum)
- New features include observability per Principle V
- Commits follow attribution rules in Principle VI

### Complexity Justification

Any violation of these principles MUST be explicitly justified:

- Document the specific need in implementation plan
- Explain why simpler alternatives were insufficient
- Get explicit approval from repository owner
- Include sunset plan for removing complexity if possible

### Runtime Development Guidance

For day-to-day development guidance compatible with this constitution, see:

- **`CLAUDE.md`** - AI assistant development guidance
- **`docs/ARCHITECTURE.md`** - System architecture details
- **`docs/TROUBLESHOOTING.md`** - Common issues and solutions
- **`docs/operations/API_RUNBOOK.md`** - Operational procedures

**Version**: 1.0.0 | **Ratified**: 2025-10-21 | **Last Amended**: 2025-10-21
