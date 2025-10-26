# Requirements Addendum: Constitution Compliance Validator

**Feature**: Constitution Compliance Validator
**Date**: 2025-10-21
**Purpose**: Address incomplete pre-implementation checklist items (27 gaps)
**Status**: Authoritative specification supplement

This document provides additional requirement specifications to complete the pre-implementation checklist. All requirements here are binding and supplement spec.md.

---

## 1. CLI Interface Completeness

### CHK007: Conflicting Flag Behavior

**Requirement**: When multiple conflicting CLI flags are provided together (e.g., `--verbose` AND `--quiet`), the validator MUST:
1. Detect the conflict during argument parsing
2. Exit with status code 2 (invalid usage)
3. Display clear error message: "Error: Conflicting flags: --verbose and --quiet cannot be used together"
4. Show hint: "Run 'validate-constitution --help' for usage information"

**Flag Precedence Rules**:
- `--verbose` and `--quiet` are MUTUALLY EXCLUSIVE
- `--dry-run` can combine with `--verbose` or `--quiet` (shows what would run in that mode)
- Last flag wins is NOT allowed - explicit conflict detection required

**Implementation**: Click's `mutually_exclusive` group or custom callback validation.

---

### CHK008: Argument Validation Error Messages

**Requirement**: All CLI argument validation errors MUST:
1. Exit with status code 2 (invalid usage, distinct from validation failures)
2. Display specific error message format:
   ```
   Error: Invalid argument <argument_name>: <specific_issue>
   Expected: <format_or_constraint>
   Example: <valid_example>
   ```
3. Suggest corrective action where applicable

**Specific Validations**:

| Argument | Validation | Error Message | Exit Code |
|----------|-----------|---------------|-----------|
| File path | Must exist | `Error: File not found: {path}` | 2 |
| File path | Must be readable | `Error: Permission denied reading: {path}` | 2 |
| Directory path | Must exist | `Error: Directory not found: {path}` | 2 |
| `--output` | Must be writable | `Error: Cannot write to {path}: {reason}` | 2 |
| Unknown flag | Invalid option | `Error: Unknown option: {flag}. Did you mean: {suggestion}?` | 2 |

**Examples**:
```bash
$ validate-constitution /nonexistent/file.py
Error: File not found: /nonexistent/file.py
Hint: Provide valid Python file or directory path

$ validate-constitution --verbosity
Error: Unknown option: --verbosity. Did you mean: --verbose?
```

---

### CHK030: Error Output Format Specification

**Requirement**: All validator output MUST follow these rules:

**stdout** (normal output):
- JSON reports (default mode)
- Human-readable summaries (`--verbose` mode)
- Violation counts (`--quiet` mode)
- Help text (`--help`)

**stderr** (error output):
- Fatal errors (missing constitution, dependencies)
- Argument validation errors
- File access errors
- Parse errors with file context
- Progress messages (when not in quiet mode)

**Exit Codes**:
| Code | Meaning | Scenario |
|------|---------|----------|
| 0 | Success | No violations found, validation passed |
| 1 | Validation failure | One or more constitutional violations detected |
| 2 | Invalid usage | Bad CLI arguments, conflicting flags |
| 3 | Fatal error | Missing constitution file, missing dependencies |
| 4 | Internal error | Unexpected exception, validator bug |
| 130 | User interrupt | Ctrl+C cancellation (SIGINT) |

**JSON Error Format** (when JSON output mode is active):
```json
{
  "error": true,
  "error_type": "fatal|usage|internal",
  "error_code": 3,
  "message": "Constitution file not found",
  "details": {
    "expected_path": ".specify/memory/constitution.md",
    "suggestion": "Restore constitution file or run from repository root"
  }
}
```

---

### CHK046: Mode Mutual Exclusivity

**Requirement**: CLI mode flags have the following combination rules:

**Mutually Exclusive**:
- `--verbose` and `--quiet` CANNOT be used together

**Composable**:
- `--dry-run` CAN combine with `--verbose` (shows detailed dry-run plan)
- `--dry-run` CAN combine with `--quiet` (shows minimal dry-run summary)
- `--output FILE` CAN combine with any mode (redirects JSON to file)

**Precedence Table**:
| Flag Combination | Result | Behavior |
|------------------|--------|----------|
| `--verbose --quiet` | ERROR | Exit with code 2, show conflict message |
| `--dry-run --verbose` | VALID | Show detailed dry-run execution plan |
| `--dry-run --quiet` | VALID | Show minimal dry-run summary (file count only) |
| `--verbose --output report.json` | VALID | Verbose JSON written to report.json |
| No flags | DEFAULT | Standard JSON output to stdout |

---

## 2. Requirement Clarity

### CHK033: Test Coverage Type Specification

**Requirement**: The 75% test coverage requirement (Principle IV, FR-015) is defined as:

**Coverage Type**: **Line coverage** (statement coverage)
- Tool: `pytest-cov` with `--cov-report=term-missing`
- Measurement: Percentage of executable lines executed during test runs
- Exclusions: Test files themselves excluded from coverage measurement
- Reporting: Coverage percentage included in `ComplianceReport.coverage_percentage`

**Rationale**: Line coverage selected over branch coverage because:
- More achievable target for minimum requirement (75% line vs ~60% branch equivalent)
- Directly supported by pytest-cov default mode
- Sufficient for detecting untested code paths
- Branch coverage can be aspirational goal (>90%) but not enforced

**Validation Logic**:
```python
coverage_result = subprocess.run(
    ["pytest", "--cov=src/constitution_validator", "--cov-report=term-missing:skip-covered"],
    capture_output=True
)
# Parse output: "TOTAL ... 78%"
if coverage_pct < 75.0:
    violation = ViolationRecord(rule_id="CONST-IV-001", ...)
```

---

### CHK039: Invalid Regex Handling in .constitution-ignore

**Requirement**: When `.constitution-ignore` contains invalid regex patterns:

**Detection**:
- Attempt to compile each pattern using `pathspec.PathSpec.from_lines()`
- Catch `re.error` or `pathspec` parsing exceptions

**Behavior**:
1. Log warning to stderr: `Warning: Invalid pattern in .constitution-ignore line {N}: {pattern}`
2. Skip invalid pattern (do not apply it)
3. Continue validation with remaining valid patterns
4. Include warning in final report metadata
5. Exit code remains 0 if no violations (warnings don't fail validation)

**Example**:
```
# .constitution-ignore
tests/**          # Valid
src/[invalid      # Invalid unclosed bracket
*.pyc             # Valid

# Output:
Warning: Invalid pattern in .constitution-ignore line 2: src/[invalid
  Error: unterminated character set at position 4
Continuing validation with 2 valid patterns...
```

**Fail-Safe Principle**: Invalid patterns degrade gracefully, don't halt validation.

---

### CHK051: Developer Satisfaction Measurement

**Requirement**: The 80% developer satisfaction metric (SC-005) is measured as follows:

**Survey Methodology**:
- **Timing**: 30 days after validator deployment
- **Sample**: All developers who committed code during the period (minimum 5 respondents)
- **Distribution**: Anonymous Google Form or similar survey tool
- **Questions** (5-point Likert scale: Strongly Disagree to Strongly Agree):
  1. "The validator helps me understand constitutional principles" (understanding)
  2. "Violation reports are clear and actionable" (clarity)
  3. "The validator catches issues I would have missed" (value)
  4. "Pre-commit integration improves my workflow" (productivity)
  5. "I would recommend this tool to other projects" (net promoter)

**Success Calculation**:
- Convert Likert responses to percentage: Agree/Strongly Agree = positive
- Success = (positive responses / total responses) ≥ 80%
- Report overall score and per-question breakdown

**Reporting**:
```markdown
## Developer Satisfaction Results (30-day post-deployment)

| Question | Positive % | Score |
|----------|-----------|-------|
| Understanding | 85% | ✓ PASS |
| Clarity | 78% | ✗ FAIL |
| Value | 90% | ✓ PASS |
| Productivity | 82% | ✓ PASS |
| Recommendation | 88% | ✓ PASS |

**Overall**: 84.6% positive (✓ Exceeds 80% target)
```

---

## 3. Edge Case Coverage

### CHK068: Circular Symlinks

**Requirement**: When validator encounters circular symlinks during directory scanning:

**Detection**:
- Track visited inodes using `os.stat().st_ino` and `st_dev`
- Detect when following symlink would revisit already-scanned inode

**Behavior**:
1. Log warning: `Warning: Circular symlink detected: {link_path} -> {target_path}`
2. Skip symlink target (do not follow)
3. Continue scanning other files
4. Include skipped symlink count in report metadata
5. Do NOT fail validation (edge case, not a violation)

**Implementation**:
```python
visited_inodes = set()

def scan_directory(path):
    stat_info = os.stat(path, follow_symlinks=False)
    inode_id = (stat_info.st_dev, stat_info.st_ino)

    if inode_id in visited_inodes:
        logger.warning(f"Circular symlink detected: {path}")
        return []  # Skip

    visited_inodes.add(inode_id)
    # Continue scanning...
```

---

### CHK071: Resuming After Transient I/O Errors

**Requirement**: For transient I/O errors (temporary permission issues, network filesystem delays):

**Retry Strategy**:
- **Retryable errors**: `PermissionError`, `OSError` with errno EAGAIN/EBUSY
- **Non-retryable errors**: `FileNotFoundError`, `IsADirectoryError`
- **Retry count**: 3 attempts with exponential backoff (100ms, 200ms, 400ms)

**Behavior**:
1. First failure: Log debug message, wait, retry
2. Second failure: Log info message, wait, retry
3. Third failure: Log error message, skip file, continue validation
4. Include skipped files in report with reason

**Fail-Safe Principle**: Transient errors skip files but don't halt validation.

**Example**:
```
INFO: Retrying read of src/example.py (attempt 1/3): Permission denied
INFO: Retrying read of src/example.py (attempt 2/3): Permission denied
ERROR: Failed to read src/example.py after 3 attempts, skipping
  Reason: PermissionError: [Errno 13] Permission denied

Validation complete: 145 files scanned, 1 file skipped
```

---

### CHK072: Corrupted Constitution Mid-Validation

**Requirement**: If constitution file becomes corrupted during validation (rare but possible):

**Detection**:
- Constitution loaded once at startup and cached
- No mid-validation re-reads required
- If cache invalidation needed (file modified), validator exits

**Behavior**:
1. **Startup**: Load constitution, compute checksum
2. **Validation**: Use cached constitution data
3. **No reload**: Constitution checksum not re-validated mid-run

**Alternative (if file watching implemented)**:
1. Detect file modification via inotify/watchdog
2. Log fatal error: `Fatal: Constitution file modified during validation`
3. Exit with code 3
4. Require re-run: "Run validation again with updated constitution"

**Current Requirement**: **No mid-validation corruption handling** - constitution is immutable once loaded.

---

### CHK073: User-Initiated Cancellation (Ctrl+C)

**Requirement**: When user presses Ctrl+C (SIGINT) during validation:

**Signal Handling**:
```python
import signal
import sys

def signal_handler(sig, frame):
    logger.info("Validation cancelled by user (Ctrl+C)")
    print("\nValidation interrupted", file=sys.stderr)
    sys.exit(130)  # Standard SIGINT exit code

signal.signal(signal.SIGINT, signal_handler)
```

**Behavior**:
1. Catch SIGINT signal
2. Log cancellation event
3. Print user-friendly message: "Validation interrupted"
4. Exit with code 130 (standard UNIX convention for SIGINT)
5. No cleanup required (no persistent state to save)
6. Partial results are NOT saved

**CI/CD Consideration**: Exit code 130 should be treated as "cancelled" not "failed" in pipelines.

---

### CHK079: File Paths with Special Characters

**Requirement**: Validator MUST handle file paths containing:
- Spaces: `src/my module/file.py`
- Unicode: `src/文件.py`, `src/файл.py`
- Quotes: `src/"quoted"/file.py` (rare but valid on POSIX)
- Newlines: Invalid on most filesystems, rejected with clear error

**Handling**:
- Use `pathlib.Path` for all path operations (handles encoding automatically)
- Quote paths in error messages: `Error: Cannot read: 'src/my module/file.py'`
- Validate paths don't contain null bytes or newlines
- Support UTF-8 encoded filenames on all platforms

**Validation**:
```python
from pathlib import Path

def validate_path(path_str: str) -> Path:
    if '\x00' in path_str or '\n' in path_str:
        raise ValueError(f"Invalid path contains forbidden characters: {path_str!r}")
    return Path(path_str)
```

---

### CHK083: Deeply Nested Directories

**Requirement**: For directory structures exceeding 100 levels of nesting:

**Behavior**:
- **No arbitrary depth limit** - follow filesystem capabilities
- Modern filesystems support 255+ levels
- Python recursion limit (default 1000) is sufficient
- Use iterative directory traversal (e.g., `os.walk`) to avoid stack overflow

**Fallback**:
- If RecursionError occurs (extremely rare):
  - Log error with path that triggered it
  - Skip subtree below recursion point
  - Continue scanning other directories
  - Exit code 4 (internal error) if this happens

**Expected**: This edge case should NEVER occur in practice with proper iterative traversal.

---

### CHK086: Future Constitution Schema Versions

**Requirement**: For backward compatibility when constitution schema evolves:

**Versioning Strategy**:
- Constitution file includes version in frontmatter: `version: 1.0.0`
- Validator supports specific version range: `1.0.0` to `1.x.x` (minor version tolerance)
- Breaking changes increment major version: `2.0.0` requires validator update

**Behavior**:
1. Parse constitution version from frontmatter
2. Check compatibility: `if major_version != SUPPORTED_MAJOR: error`
3. Warn on minor version mismatch: `Warning: Constitution v1.2 detected, validator supports v1.0-1.1. Some features may not work.`
4. Reject incompatible versions: `Fatal: Constitution v2.0 not supported by validator v1.x`

**Migration Path** (see CHK128 below).

---

### CHK090: Corrupted Dependency Detection

**Requirement**: When required dependencies (pytest-cov, git, Click) are installed but corrupted:

**Detection**:
1. Import validation: Try to import each required package
2. Version check: Verify minimum version meets requirements
3. Functional test: Execute simple command (e.g., `git --version`, `pytest --version`)

**Behavior**:
```python
try:
    import git
    git.Repo(".")  # Functional test
except ImportError:
    error("GitPython not installed. Install with: pip install GitPython")
except git.exc.InvalidGitRepositoryError:
    # Expected if not in git repo - this is OK
    pass
except Exception as e:
    error(f"GitPython installation appears corrupted: {e}")
    error("Reinstall with: pip uninstall GitPython && pip install GitPython")
```

**Corrupted Dependency Scenarios**:
- ImportError → Missing package
- AttributeError on import → Corrupted installation
- Version mismatch → Wrong version installed

---

### CHK097: Files with Execute Permissions

**Requirement**: When validator encounters Python files with execute bit set:

**Behavior**:
- **No special handling** - execute permissions are irrelevant to validation
- Scan file normally if it matches `.py` extension
- Executable scripts (with shebang) are valid Python files

**Security Note**: Validator does NOT execute any code, only parses AST. Execute permissions are informational only.

---

## 4. Usability Requirements

### CHK098: Progress Indicators

**Requirement**: During validation, display progress to stderr (suppressed in `--quiet` mode):

**Progress Format**:
```
Scanning codebase... 45/150 files (30%)
Validating Principle I: Unified Agent Architecture... ✓
Validating Principle II: Centralized Configuration... 5 violations
Validating Principle III: Dual-Database RAG... ✓
Validating Principle IV: Test Coverage... ✓ (78.5%)
Validating Principle V: Observability... 2 violations
Validating Principle VI: Git Attribution... ✓
Generating report...
```

**Implementation**:
- Use `tqdm` or custom progress printing
- Update every 10 files or 5% progress
- Clear progress line before final output (or use stderr)
- Disable in `--quiet` mode or when stderr is not a TTY

---

### CHK099: Colorized Terminal Output

**Requirement**: Human-readable text output includes ANSI color codes when stderr is a TTY:

**Color Scheme**:
- ✓ Green: Passed principles, success messages
- ✗ Red: Failed principles, violations
- Yellow: Warnings, skipped files
- Cyan: Progress indicators, file paths
- White: Normal text

**Implementation**:
```python
from colorama import init, Fore, Style
init(autoreset=True)  # Auto-reset colors

def colorize(text: str, color: str) -> str:
    if not sys.stderr.isatty():
        return text  # No colors for non-TTY
    return f"{color}{text}{Style.RESET_ALL}"

print(colorize("✓ Principle I: Passed", Fore.GREEN))
print(colorize("✗ Principle II: 5 violations", Fore.RED))
```

**Disable Colors**:
- When `--quiet` mode
- When stderr is not a TTY (piped/redirected)
- When `NO_COLOR` environment variable is set

---

### CHK101: Command Autocomplete

**Requirement**: Provide shell autocomplete scripts for bash and zsh:

**Distribution**:
- Include autocomplete scripts in repository: `scripts/autocomplete/validate-constitution.bash`, `scripts/autocomplete/validate-constitution.zsh`
- Installation instructions in README
- Use Click's built-in autocomplete support

**Implementation**:
```python
# In cli.py
import click

@click.command()
@click.option('--verbose', is_flag=True, help='Verbose output')
@click.option('--quiet', is_flag=True, help='Quiet mode')
# Click generates autocomplete automatically

# Generate completion scripts:
# _VALIDATE_CONSTITUTION_COMPLETE=bash_source validate-constitution > scripts/autocomplete/validate-constitution.bash
```

**User Installation**:
```bash
# Bash
source scripts/autocomplete/validate-constitution.bash

# Zsh
source scripts/autocomplete/validate-constitution.zsh
```

---

## 5. Compatibility Requirements

### CHK104: Git Version Compatibility

**Requirement**: Minimum Git version required: **Git 2.25.0** (released January 2020)

**Rationale**:
- Supports `git log --format=%an %ae` (author extraction)
- Supports `git diff --staged --name-only` (pre-commit integration)
- Available on Ubuntu 20.04 LTS and later

**Validation**:
```python
git_version = subprocess.check_output(["git", "--version"]).decode()
# Output: "git version 2.25.1"
version_str = git_version.split()[2]  # "2.25.1"
major, minor, patch = map(int, version_str.split('.'))

if (major, minor) < (2, 25):
    error(f"Git 2.25.0+ required, found {version_str}")
    error("Upgrade with: sudo apt update && sudo apt install git")
```

---

### CHK109: Missing Directory Structure Detection

**Requirement**: When validator runs on repository missing expected directories:

**Expected Structure**:
- `src/` - Source code directory
- `tests/` - Test directory
- `.git/` - Git repository (optional if using `--no-git` flag)

**Behavior**:
1. Check for `src/` directory existence
2. If missing: Log warning: `Warning: src/ directory not found. Is this a Luminari Agent repository?`
3. Continue validation on files found in current directory
4. If zero Python files found: Exit with error: `Fatal: No Python files found to validate`

**No Strict Requirement**: Validator should work on any Python codebase, not just Luminari Agent structure.

---

### CHK111: Dependency Security Vulnerabilities

**Requirement**: When required dependencies have known security vulnerabilities:

**Detection**:
- **Manual**: Run `pip-audit` or `safety check` before validator installation
- **Automatic**: Include `pip-audit` in CI/CD pipeline
- Validator itself does NOT scan for vulnerabilities (out of scope)

**Mitigation**:
- Pin dependency versions in `pyproject.toml`
- Use `pip-audit` in pre-commit hooks
- Update dependencies regularly (monthly security review)

**Example** (`pyproject.toml`):
```toml
dependencies = [
    "click>=8.1.0,<9.0",  # Known secure version range
    "GitPython>=3.1.40",  # CVE-2023-40267 fixed in 3.1.40
    "pathspec>=0.11.0",
]
```

**Vulnerability Response**:
1. Security advisory published for dependency
2. Update `pyproject.toml` with patched version
3. Release new validator version
4. Notify users via release notes

---

### CHK112: Dependency Conflicts with Luminari Agent

**Requirement**: Ensure validator dependencies don't conflict with Luminari Agent's existing dependencies:

**Strategy**:
- Review `pyproject.toml` for version overlaps
- Use compatible version ranges, not exact pins
- Test validator installation in Luminari Agent virtualenv

**Known Dependencies** (Luminari Agent):
- `pydantic>=2.0` (required by validator models)
- `pytest>=7.0` (required by pytest-cov)
- `click>=8.0` (validator CLI)

**Conflict Resolution**:
1. Use version ranges compatible with both: `pydantic>=2.0,<3.0`
2. Prefer minimal dependencies (no heavy ML libraries)
3. Test installation: `pip install -e .[dev,validator]` should succeed

**Validation**:
```bash
# Test for conflicts
pip install -e .[dev]  # Luminari Agent dependencies
pip install GitPython pathspec click  # Validator dependencies
# Should complete without conflicts
```

---

## 6. Specification Gaps

### CHK126: Validator Bug Behavior (Fail-Safe vs Fail-Open)

**Requirement**: When the validator itself has a bug (unexpected exception):

**Philosophy**: **Fail-Safe** - Don't block development, but notify loudly

**Behavior**:
1. Catch unexpected exceptions in top-level exception handler
2. Log full traceback to stderr
3. Print user-friendly error: `Internal validator error occurred. Please report this bug.`
4. Generate partial report if any violations were detected before crash
5. Exit with code 4 (internal error)
6. Include bug report URL in error message

**Example**:
```python
try:
    report = run_validation()
except Exception as e:
    logger.exception("Unexpected validator error")
    print(f"Internal Error: {e}", file=sys.stderr)
    print("Please report this bug: https://github.com/user/repo/issues", file=sys.stderr)
    if partial_violations:
        print(f"Partial results: {len(partial_violations)} violations detected before crash")
    sys.exit(4)
```

**CI/CD Impact**: Exit code 4 should trigger alerts but not block merges (treat as validator bug, not code violation).

---

### CHK128: Constitution Migration Path

**Requirement**: When constitution schema is updated (major version change):

**Migration Strategy**:
1. **Announce**: Release notes explain breaking changes
2. **Validate**: New validator version checks for old constitution format
3. **Assist**: Provide migration script if needed
4. **Coexist**: Support transition period (2 weeks) where both versions work

**Example Migration** (v1.0 → v2.0):
```bash
# Validator detects old constitution
$ validate-constitution
Warning: Constitution v1.0 detected. Validator v2.0 requires v2.0 schema.
Run migration: python scripts/migrate_constitution.py --from 1.0 --to 2.0
Or downgrade validator: pip install constitution-validator==1.x

# Migration script
$ python scripts/migrate_constitution.py --from 1.0 --to 2.0
Constitution migrated: .specify/memory/constitution.md
Changes:
  - Added new principle VII: Cloud-Native Architecture
  - Renamed principle IV: Test-Driven Quality → Quality Assurance
Review changes and commit.
```

**Backward Compatibility**: Minor versions (1.0 → 1.1) are backward compatible, no migration needed.

---

## 7. Documentation Requirements

### CHK137: Glossary / Terminology

**Requirement**: Include glossary section in validator documentation:

**Glossary** (to be added to `quickstart.md`):

| Term | Definition |
|------|------------|
| **Constitution** | The authoritative document (`.specify/memory/constitution.md`) defining governance principles |
| **Principle** | One of six architectural rules (I-VI) that code must follow |
| **Validation Rule** | Specific automated check for a principle (e.g., "detect os.getenv()") |
| **Violation** | Instance where code breaks a validation rule |
| **Violation Group** | Set of violations of the same type (e.g., all "direct os.getenv()" violations) |
| **Compliance Report** | JSON output containing all validation results |
| **Suppression** | Intentional exception via `# noqa: CONST-X-XXX` comment |
| **Remediation** | Suggested fix for a violation |
| **Confidence Level** | Accuracy estimate for violation detection (high/medium/low) |
| **.constitution-ignore** | File specifying paths to exclude from validation |

---

### CHK138: Visual Diagrams

**Requirement**: Include architecture diagrams in documentation:

**Diagrams to Create**:

1. **Validation Pipeline Flow** (validation-flow.png):
   ```
   [Load Constitution] → [Discover Files] → [Apply Ignore Patterns]
          ↓
   [Execute 6 Principle Rules in Parallel]
          ↓
   [Collect Violations] → [Group by Type] → [Generate Report] → [Exit with Code]
   ```

2. **Report Structure** (report-structure.png):
   ```
   ComplianceReport
   ├── Metadata (version, timestamp, duration)
   ├── Scan Summary (files scanned, excluded)
   ├── Overall Results (passed, violation counts)
   └── Principle Summaries (6)
       └── Violation Groups (by type)
           └── Locations (file:line)
   ```

3. **Pre-Commit Integration** (pre-commit-flow.png):
   ```
   [git commit] → [pre-commit hook] → [validate-constitution --staged]
                                              ↓
                                    [Violations found?]
                                       ↙           ↘
                                [Block commit]   [Allow commit]
                                [Show summary]
   ```

**Format**: Mermaid diagrams in markdown (auto-rendered on GitHub) + PNG exports.

---

## Summary of Addressed Gaps

| Checklist Item | Category | Status | Location in Document |
|----------------|----------|--------|---------------------|
| CHK007 | CLI | ✓ Specified | §1.1 Conflicting Flag Behavior |
| CHK008 | CLI | ✓ Specified | §1.2 Argument Validation Errors |
| CHK030 | Error Handling | ✓ Specified | §1.3 Error Output Format |
| CHK033 | Requirements | ✓ Specified | §2.1 Test Coverage Type |
| CHK039 | Error Handling | ✓ Specified | §2.2 Invalid Regex Handling |
| CHK046 | CLI | ✓ Specified | §1.4 Mode Mutual Exclusivity |
| CHK051 | Success Criteria | ✓ Specified | §2.3 Developer Satisfaction Measurement |
| CHK068 | Edge Cases | ✓ Specified | §3.1 Circular Symlinks |
| CHK071 | Recovery | ✓ Specified | §3.2 Transient I/O Errors |
| CHK072 | Recovery | ✓ Specified | §3.3 Corrupted Constitution Mid-Validation |
| CHK073 | Recovery | ✓ Specified | §3.4 User Cancellation (Ctrl+C) |
| CHK079 | Edge Cases | ✓ Specified | §3.5 File Paths with Special Characters |
| CHK083 | Edge Cases | ✓ Specified | §3.6 Deeply Nested Directories |
| CHK086 | Compatibility | ✓ Specified | §3.7 Future Constitution Schema Versions |
| CHK090 | Dependencies | ✓ Specified | §3.8 Corrupted Dependency Detection |
| CHK097 | Edge Cases | ✓ Specified | §3.9 Files with Execute Permissions |
| CHK098 | Usability | ✓ Specified | §4.1 Progress Indicators |
| CHK099 | Usability | ✓ Specified | §4.2 Colorized Output |
| CHK101 | Usability | ✓ Specified | §4.3 Command Autocomplete |
| CHK104 | Compatibility | ✓ Specified | §5.1 Git Version Compatibility |
| CHK109 | Dependencies | ✓ Specified | §5.2 Missing Directory Structure |
| CHK111 | Security | ✓ Specified | §5.3 Dependency Security Vulnerabilities |
| CHK112 | Dependencies | ✓ Specified | §5.4 Dependency Conflicts |
| CHK126 | Error Handling | ✓ Specified | §6.1 Validator Bug Behavior |
| CHK128 | Migration | ✓ Specified | §6.2 Constitution Migration Path |
| CHK137 | Documentation | ✓ Specified | §7.1 Glossary / Terminology |
| CHK138 | Documentation | ✓ Specified | §7.2 Visual Diagrams |

**All 27 incomplete checklist items are now fully specified.**

---

## Integration with Existing Specifications

This document supplements but does not replace:
- **spec.md**: Functional requirements (FR-001 through FR-024)
- **plan.md**: Technical implementation strategy
- **data-model.md**: Entity definitions and relationships
- **contracts/**: JSON schema specifications

Where conflicts arise, this document takes precedence for the 27 items addressed above.

---

## Changelog

- **2025-10-21**: Initial version addressing all 27 pre-implementation checklist gaps
