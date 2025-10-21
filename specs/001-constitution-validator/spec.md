# Feature Specification: Constitution Compliance Validator

**Feature Branch**: `001-constitution-validator`
**Created**: 2025-10-21
**Status**: Draft
**Input**: User description: "Add a CLI command to validate constitution compliance"

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

- What happens when the constitution file is missing or corrupted?
- How does the validator handle files that are generated code or third-party dependencies?
- What happens when running the validator on a partial checkout or shallow clone?
- How does the validator perform on large codebases (>100k LOC)?
- What happens when running in CI/CD pipelines with limited permissions?
- How does the validator handle symlinks or files outside the repository root?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST validate code against all six constitutional principles (Unified Agent, Centralized Configuration, Dual-Database RAG, Test-Driven Quality, Observability, Git Attribution)
- **FR-002**: System MUST scan the entire codebase for principle violations when run without arguments
- **FR-003**: System MUST support targeted validation of specific files or directories passed as arguments
- **FR-004**: System MUST generate a detailed compliance report listing all violations with file paths and line numbers
- **FR-005**: System MUST provide remediation guidance for each violation type
- **FR-006**: System MUST exit with non-zero status code when violations are found
- **FR-007**: System MUST exit with zero status code when no violations are found
- **FR-008**: System MUST support a verbose mode that shows all checks performed, not just violations
- **FR-009**: System MUST support a quiet mode that only outputs violation counts for scripting
- **FR-010**: System MUST ignore specified paths via configuration file (.constitution-ignore or similar)
- **FR-011**: System MUST complete validation within reasonable time (under 30 seconds for typical codebase)
- **FR-012**: System MUST provide clear error messages when unable to parse files or access directories
- **FR-013**: System MUST support integration with pre-commit hooks via standard hook interface
- **FR-014**: System MUST validate git commit messages against attribution rules when checking commit history
- **FR-015**: System MUST measure and report test coverage percentage when validating Principle IV
- **FR-016**: System MUST detect direct database client usage that bypasses centralized configuration
- **FR-017**: System MUST verify both PostgreSQL and Neo4j clients are properly configured when validating Principle III
- **FR-018**: System MUST scan for missing logging/metrics instrumentation in new feature code when validating Principle V
- **FR-019**: System MUST support dry-run mode that shows what would be checked without performing full validation
- **FR-020**: System MUST load constitution from .specify/memory/constitution.md as the source of truth

### Key Entities

- **Validation Rule**: Represents a specific constitutional principle check (e.g., "No multiple agent files"), includes check logic, violation message template, and remediation guidance
- **Violation Record**: Captures details of a detected violation including file path, line number, principle violated, description, and suggested fix
- **Compliance Report**: Aggregates all violation records, groups by principle, provides summary statistics and overall pass/fail status
- **Ignore Pattern**: Defines file paths or patterns to exclude from validation (e.g., third-party code, generated files)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can validate their code against all six constitutional principles in under 30 seconds for a typical codebase
- **SC-002**: 95% of constitutional violations are automatically detected by the validator without manual code review
- **SC-003**: Validation reports include actionable remediation steps for 100% of detected violations
- **SC-004**: Pre-commit integration blocks non-compliant commits with zero false positives in standard development workflows
- **SC-005**: Developer satisfaction: 80% of developers report the validator helps them understand and follow constitutional principles
- **SC-006**: Constitutional drift reduction: Number of violations in merged code decreases by 90% within 30 days of validator deployment
- **SC-007**: Validation overhead: Pre-commit validation adds less than 5 seconds to normal commit workflow
- **SC-008**: Accuracy: False positive rate below 5% based on manual review of flagged violations

### Assumptions

- Developers have read access to .specify/memory/constitution.md
- The repository structure follows Base Agent conventions (src/, tests/, docs/)
- Git is available for commit message validation
- Test coverage tooling (pytest-cov) is already configured in the project
- Developers understand basic command-line interface usage
- Pre-commit framework is already installed in the development environment
- The constitution file format remains stable (versioned with semantic versioning)
