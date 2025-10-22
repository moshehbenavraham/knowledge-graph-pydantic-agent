# Implementation Plan: Constitution Compliance Validator

**Branch**: `001-constitution-validator` | **Date**: 2025-10-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-constitution-validator/spec.md`

## Summary

Build a Python 3.11+ CLI tool that validates code changes against the six constitutional principles (Unified Agent Architecture, Centralized Configuration, Dual-Database RAG, Test-Driven Quality, Observability, Git Attribution). The validator performs AST-based code analysis, integrates with pytest-cov for coverage validation, checks git commit messages, and outputs structured JSON reports grouping violations by type with all affected file locations. Designed for pre-commit hook integration with fail-fast error handling for missing dependencies.

## Technical Context

**Language/Version**: Python 3.11+ (matching Base Agent requirements)
**Primary Dependencies**: Click (CLI), ast (code analysis), GitPython (commit validation), pytest-cov (coverage), pathspec (.gitignore patterns)
**Storage**: File-based (reads .specify/memory/constitution.md, .constitution-ignore)
**Testing**: pytest with 75%+ coverage requirement
**Target Platform**: Linux/macOS/WSL development environments
**Project Type**: Single (CLI tool integrated into existing Base Agent repository)
**Performance Goals**: <30s full codebase validation, <5s pre-commit validation (incremental)
**Constraints**: Zero dependencies on runtime databases, must work in air-gapped environments
**Scale/Scope**: ~10-50k LOC codebases, validate against 6 principles with ~20-30 rule checks

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Unified Agent Architecture
- ✅ **PASS** - This feature does NOT add a new agent; it's a CLI validation tool
- ✅ No modifications to `src/agent/unified_agent.py` required
- ✅ No new agent implementations

### II. Type-Safe Centralized Configuration
- ✅ **PASS** - Validator will CHECK for violations of this principle in scanned code
- ✅ Validator itself will use configuration from `.specify/memory/constitution.md` (file-based, not env vars)
- ⚠️ **NOTE**: Validator configuration (if needed) should use centralized config pattern

### III. Dual-Database Agentic RAG
- ✅ **PASS** - Validator does not interact with databases
- ✅ Validator will CHECK that database clients are properly configured in scanned code
- ✅ No PostgreSQL/Neo4j dependencies for the validator itself

### IV. Test-Driven Quality Assurance
- ✅ **MUST MEET** - Validator must achieve 75%+ test coverage
- ✅ Unit tests required for all validation rules (testable via mock codebases)
- ✅ Integration tests with sample violation scenarios
- ✅ Pre-commit hooks must pass before merge

### V. Production-Ready Observability
- ✅ **MUST MEET** - Validator must include structured logging
- ✅ Log validation progress, rule execution, and errors
- ✅ JSON output format provides observability for CI/CD pipelines
- ⚠️ **NOTE**: Consider adding metrics for validation time per principle

### VI. Git Attribution & Contribution Standards
- ✅ **MUST MEET** - All commits follow standard attribution (no AI co-author)
- ✅ Conventional Commits format required
- ✅ Validator will CHECK commit messages for AI attribution violations

**Overall Assessment**: ✅ **PASSES** all constitutional gates. No violations to justify.

## Project Structure

### Documentation (this feature)

```
specs/001-constitution-validator/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification (completed)
├── research.md          # Phase 0 output (to be generated)
├── data-model.md        # Phase 1 output (to be generated)
├── quickstart.md        # Phase 1 output (to be generated)
├── contracts/           # Phase 1 output (JSON schemas)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```
src/
├── constitution_validator/           # New module
│   ├── __init__.py
│   ├── cli.py                        # Click CLI entry point
│   ├── loader.py                     # Constitution file parser
│   ├── rules/                        # Validation rule implementations
│   │   ├── __init__.py
│   │   ├── base.py                   # Base ValidationRule class
│   │   ├── principle_i.py            # Unified Agent checks
│   │   ├── principle_ii.py           # Config centralization checks
│   │   ├── principle_iii.py          # Database architecture checks
│   │   ├── principle_iv.py           # Test coverage checks
│   │   ├── principle_v.py            # Observability checks
│   │   └── principle_vi.py           # Git attribution checks
│   ├── scanners/                     # Code analysis engines
│   │   ├── __init__.py
│   │   ├── ast_scanner.py            # AST-based Python analysis
│   │   ├── git_scanner.py            # Git commit message scanner
│   │   └── coverage_scanner.py       # pytest-cov integration
│   ├── models.py                     # Pydantic models (ViolationRecord, Report)
│   └── reporter.py                   # JSON report generation

tests/
├── unit/
│   └── constitution_validator/
│       ├── test_rules_principle_i.py
│       ├── test_rules_principle_ii.py
│       ├── test_rules_principle_iii.py
│       ├── test_rules_principle_iv.py
│       ├── test_rules_principle_v.py
│       ├── test_rules_principle_vi.py
│       ├── test_cli.py
│       └── test_reporter.py
└── integration/
    └── constitution_validator/
        ├── test_full_validation.py
        └── fixtures/                 # Sample codebases with violations
            ├── valid_codebase/
            └── violation_samples/

.pre-commit-config.yaml              # Updated with constitution validator hook
.constitution-ignore                  # New file (optional ignore patterns)
pyproject.toml                        # Updated with new CLI entry point
```

**Structure Decision**: Single project structure (Option 1) as this is a CLI tool integrated into the existing Base Agent repository. No separate frontend/backend or mobile components. All code lives under `src/constitution_validator/` with corresponding test structure.

## Complexity Tracking

### Principle II Configuration Exemption

**Issue**: Validator uses structlog configuration in `src/constitution_validator/__init__.py` rather than centralized `src/config/settings.py`.

**Justification**: This is library initialization, not user-facing configuration. structlog setup (formatter, processors, context) is hardcoded to validator needs and doesn't require runtime customization. The validator reads its operational parameters from constitution file, not environment variables.

**Decision**: Exempted. Logging library setup is distinct from application configuration per Principle II intent (prevent scattered `os.getenv()` calls). Alternative would add unnecessary complexity for zero user benefit.

**Mitigation**: Validator enforces Principle II in scanned code but uses standard library initialization patterns for its own logging infrastructure.

---

## Phase 0: Research & Design Decisions

**Status**: To be generated

Key research areas identified from Technical Context:
1. AST parsing patterns for Python code analysis (detecting os.getenv, agent files, etc.)
2. Git commit message parsing strategies (GitPython vs subprocess)
3. pytest-cov programmatic API integration
4. Click CLI best practices for structured output (JSON + human-readable error messages)
5. Pre-commit hook integration patterns
6. .gitignore-style pattern matching libraries (pathspec evaluation)

**Output**: `research.md` will document decisions, rationale, and alternatives for each area.

---

## Phase 1: Data Model & Contracts

**Status**: To be generated

**Planned Outputs**:
- `data-model.md`: Entity definitions (Constitution, ValidationRule, ViolationRecord, ComplianceReport, IgnorePattern)
- `contracts/`: JSON schemas for report output format
- `quickstart.md`: Developer guide for running validator and interpreting results

**Agent Context Update**: Will run `.specify/scripts/bash/update-agent-context.sh claude` after Phase 1 design complete.

---

## Next Steps

1. Execute Phase 0: Generate `research.md` (automated by /speckit.plan)
2. Execute Phase 1: Generate `data-model.md`, `contracts/`, `quickstart.md` (automated by /speckit.plan)
3. Run `/speckit.tasks` to generate implementation task breakdown
4. Begin implementation following task order
