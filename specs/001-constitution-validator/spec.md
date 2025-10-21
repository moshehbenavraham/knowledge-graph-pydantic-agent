# Feature Specification: Constitution Compliance Validator

**Feature Branch**: `001-constitution-validator`
**Created**: 2025-10-21
**Status**: Draft
**Input**: User description: "Add a CLI command to validate constitution compliance"

## Clarifications

### Session 2025-10-21

- Q: What output format should the compliance report use? → A: JSON only (structured output)
- Q: How should the validator handle missing dependencies (pytest-cov, git)? → A: Fail with clear error message
- Q: What implementation language should be used? → A: Python 3.11+
- Q: How should duplicate violations be handled (same violation in multiple locations)? → A: Group by violation type, list all locations
- Q: What happens when constitution file is missing or corrupted? → A: Fatal error, cannot validate

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic Constitution Compliance Check (Priority: P1)

As a developer working on Base Agent, I need to validate my code changes against the six constitutional principles before committing, so I can ensure my work adheres to project governance standards and catch violations early.

**Why this priority**: This is the core value proposition. Developers need immediate feedback on compliance violations to prevent constitutional drift. Without this, the constitution becomes documentation that's ignored rather than enforced.

**Independent Test**: Can be fully tested by running the validator on a sample codebase with known violations (e.g., multiple agent files, direct os.getenv() calls) and verifying it detects and reports all violations correctly.

**Acceptance Scenarios**:

1. **Given** I have made changes to agent code, **When** I run the compliance validator, **Then** it checks for violations of Principle I (Unified Agent Architecture) and reports any additional agent files found
2. **Given** I have added new configuration code, **When** I run the compliance validator, **Then** it checks for violations of Principle II (Centralized Configuration) and reports any direct os.getenv() usage
3. **Given** I have modified database code, **When** I run the compliance validator, **Then** it checks for violations of Principle III (Dual-Database RAG) and reports if either PostgreSQL or Neo4j connections are removed
4. **Given** I have added new functions, **When** I run the compliance validator, **Then** it checks for violations of Principle IV (Test-Driven Quality) and reports missing tests or coverage below 75%
5. **Given** I have created new features, **When** I run the compliance validator, **Then** it checks for violations of Principle V (Observability) and reports missing logging or metrics
6. **Given** I have made commits, **When** I run the compliance validator, **Then** it checks for violations of Principle VI (Git Attribution) and reports any AI attribution in commit messages

---

### User Story 2 - Detailed Violation Reports (Priority: P2)

As a developer who receives compliance violations, I need detailed reports explaining what was violated and how to fix it, so I can quickly understand and remediate the issues without having to manually read the entire constitution.

**Why this priority**: Detection alone isn't enough - developers need actionable guidance. This transforms the validator from a "pass/fail" tool into a teaching tool that helps developers learn and apply constitutional principles.

**Independent Test**: Can be tested by triggering specific violations and verifying the report includes file paths, line numbers, violation descriptions, relevant constitutional principle quotes, and fix suggestions.

**Acceptance Scenarios**:

1. **Given** the validator detects a violation, **When** I view the report, **Then** it shows the exact file path and line number where the violation occurred
2. **Given** the validator detects a violation, **When** I view the report, **Then** it includes a quote from the relevant constitutional principle explaining why this is prohibited
3. **Given** the validator detects a violation, **When** I view the report, **Then** it provides specific remediation steps (e.g., "Move this to src/config/settings.py and use get_settings()")
4. **Given** multiple violations exist, **When** I view the report, **Then** violations are grouped by constitutional principle for easy understanding

---

### User Story 3 - Pre-Commit Hook Integration (Priority: P3)

As a developer, I want the constitution validator to run automatically before each commit, so compliance is enforced without me having to remember to run manual checks.

**Why this priority**: Automation ensures consistent enforcement. While manual validation is useful, pre-commit integration prevents violations from ever entering the codebase, reducing technical debt and rework.

**Independent Test**: Can be tested by configuring the pre-commit hook, making a commit with violations, and verifying the commit is blocked with a clear error message directing to the validation report.

**Acceptance Scenarios**:

1. **Given** the pre-commit hook is enabled, **When** I attempt to commit code with violations, **Then** the commit is blocked and I see a summary of violations
2. **Given** the pre-commit hook is enabled, **When** I attempt to commit compliant code, **Then** the commit proceeds without delays or false positives
3. **Given** the pre-commit hook is enabled, **When** validation fails, **Then** I am shown the command to view the detailed report
4. **Given** I need to bypass validation temporarily, **When** I use a documented bypass flag, **Then** the commit proceeds with a warning logged

---

### Edge Cases

- **Missing or corrupted constitution file**: Validator exits immediately with fatal error and non-zero status code, instructing user to restore .specify/memory/constitution.md (e.g., "Fatal: Constitution file not found at .specify/memory/constitution.md. Cannot validate without constitution.")
- **Missing dependencies (pytest-cov, git)**: Validator exits immediately with non-zero status code and clear error message showing which dependency is missing and installation command (e.g., "Error: pytest-cov not found. Install with: pip install pytest-cov")
- **Generated code or third-party dependencies**: Validator uses .constitution-ignore file with default patterns for common generated/vendor paths (build/, dist/, vendor/, *.egg-info/, node_modules/, __pycache__/)
- **Partial checkout or shallow clone**: Validator operates on available files only; git commit validation skipped if git history unavailable
- **Large codebases (>100k LOC)**: Validator may exceed 30s threshold; users should use targeted validation (FR-003) or incremental mode for pre-commit
- **CI/CD pipelines with limited permissions**: Validator handles permission denied errors gracefully per FR-012, skips inaccessible directories with warning
- **Symlinks or files outside repository root**: Validator follows symlinks but only validates files within repository root; external files logged as skipped

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST validate code against all six constitutional principles (Unified Agent, Centralized Configuration, Dual-Database RAG, Test-Driven Quality, Observability, Git Attribution)
- **FR-002**: System MUST scan the entire codebase for principle violations when run without arguments
- **FR-003**: System MUST support targeted validation of specific files or directories passed as arguments
- **FR-004**: System MUST generate a detailed compliance report in JSON format that groups violations by rule_id (violation type) and lists all file paths and line numbers for each violation group
- **FR-005**: System MUST provide remediation guidance for each violation type
- **FR-006**: System MUST exit with non-zero status code when violations are found
- **FR-007**: System MUST exit with zero status code when no violations are found
- **FR-008**: System MUST support a verbose mode that shows all checks performed, not just violations
- **FR-009**: System MUST support a quiet mode that only outputs violation counts for scripting
- **FR-010**: System MUST ignore specified paths via .constitution-ignore configuration file using gitignore-style glob patterns (parsed via pathspec library)
- **FR-011**: System MUST complete validation within 30 seconds for typical codebase (defined as 10,000-50,000 lines of Python code across 100-500 files)
- **FR-012**: System MUST provide clear error messages when unable to parse files or access directories, including: file path, line number (for parse errors), error type, and suggested resolution
- **FR-013**: System MUST support integration with pre-commit hooks via standard hook interface
- **FR-014**: System MUST validate git commit messages against attribution rules (Principle VI) for unpushed commits only (commits ahead of origin/main or origin/master)
- **FR-015**: System MUST measure and report test coverage percentage when validating Principle IV
- **FR-016**: System MUST detect direct database client usage that bypasses centralized configuration
- **FR-017**: System MUST verify both PostgreSQL and Neo4j clients are properly configured when validating Principle III (defined as: clients instantiated via centralized configuration in src/config/clients.py or src/config/settings.py, not via direct constructor calls in application code)
- **FR-018**: System MUST scan for missing logging/metrics instrumentation when validating Principle V (defined as: public functions >5 lines without logger imports or logging calls, excluding test files and trivial property accessors)
- **FR-019**: System MUST support dry-run mode that shows what would be checked without performing full validation
- **FR-020**: System MUST load constitution from .specify/memory/constitution.md as the source of truth
- **FR-021**: System MUST validate presence of required dependencies (pytest-cov, git) at startup and exit with clear error message including installation instructions if any are missing
- **FR-022**: System MUST verify constitution file (.specify/memory/constitution.md) exists and is readable at startup, and exit with fatal error if missing or corrupted
- **FR-023**: System MUST handle generated code and third-party dependencies by excluding common patterns via default .constitution-ignore rules (build/, dist/, vendor/, *.egg-info/, node_modules/, __pycache__/, .venv/, venv/, .git/)
- **FR-024**: System MUST support inline violation suppression via comments in format `# noqa: CONST-{principle}-{number}` with optional reason, and report suppressed violations separately in JSON output

### Key Entities

- **Validation Rule**: Represents a specific constitutional principle check (e.g., "No multiple agent files"), includes check logic, violation message template, and remediation guidance
- **Violation Record**: Captures details of a detected violation including file path, line number, principle violated, description, and suggested fix
- **Compliance Report**: JSON-structured output that aggregates all violation records, groups by Principle and rule_id (with all file locations listed under each violation group), provides summary statistics and overall pass/fail status
- **Ignore Pattern**: Defines file paths or patterns to exclude from validation (e.g., third-party code, generated files)

### Technical Constraints

- **Language**: Python 3.11+ (matching Base Agent project requirements)
- **CLI Framework**: Click for command-line interface
- **Code Analysis**: AST-based parsing for Python code validation
- **Git Integration**: GitPython for commit message validation
- **Coverage Tool**: pytest-cov integration for test coverage measurement
- **Logging**: structlog for structured logging per Principle V (observability requirement)
- **Pattern Matching**: pathspec library for gitignore-style .constitution-ignore patterns

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can validate their code against all six constitutional principles in under 30 seconds for a typical codebase (10,000-50,000 LOC)
- **SC-002**: 95% of constitutional violations are automatically detected by the validator without manual code review (measured via manual test corpus of 100+ known violations across all 6 principles)
- **SC-003**: Validation reports include actionable remediation steps for 100% of detected violations
- **SC-004**: Pre-commit integration blocks non-compliant commits with zero false positives in standard development workflows
- **SC-005**: Developer satisfaction: 80% of developers report the validator helps them understand and follow constitutional principles
- **SC-006**: Constitutional drift reduction: Number of violations in merged code decreases by 90% within 30 days of validator deployment
- **SC-007**: Validation overhead: Pre-commit validation adds less than 5 seconds to normal commit workflow
- **SC-008**: Accuracy: False positive rate below 5% based on manual review of flagged violations (measured via validation against real Base Agent codebase with manual classification of 100+ flagged items)

### Assumptions

- Developers have read access to constitution file (.specify/memory/constitution.md)
- The repository structure follows Base Agent conventions (src/, tests/, docs/)
- Git is available for commit message validation
- Test coverage tooling (pytest-cov) is already configured in the project
- Developers understand basic command-line interface usage
- Pre-commit framework is already installed in the development environment
- The constitution file format remains stable (versioned with semantic versioning)
- Python 3.11+ is installed and available in the development environment
