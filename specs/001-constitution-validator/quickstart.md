# Constitution Compliance Validator - Quickstart Guide

**Get started with the Constitution Compliance Validator in 5 minutes.**

---

## Installation

Install the validator with its dependencies:

```bash
pip install -e .[dev]
```

Required dependencies (automatically installed):
- `click` - CLI framework
- `GitPython` - Git commit analysis
- `coverage` - Coverage validation
- `pathspec` - .gitignore pattern matching

---

## Basic Usage

### Full Codebase Validation

Scan the entire codebase against all six constitutional principles:

```bash
constitution-validate
```

**Output**: JSON report with violations grouped by principle (exit code 1 if violations found, 0 if clean).

### Validate Specific Files

Target specific files or directories:

```bash
constitution-validate src/config/settings.py src/agent/
```

### Verbose Mode

See all checks performed, not just violations:

```bash
constitution-validate --verbose
```

### Quiet Mode

Show only violation counts (useful for CI/CD):

```bash
constitution-validate --quiet
```

---

## Understanding Output

### JSON Report Structure

```json
{
  "passed": false,
  "total_violations": 12,
  "principles": {
    "I": {
      "name": "Unified Agent Architecture",
      "violations": [
        {
          "type": "multiple_agents",
          "files": [
            {"path": "src/custom_agent.py", "line": 45}
          ],
          "message": "Agent class 'CustomAgent' found outside unified_agent.py",
          "remediation": "Move functionality to src/agent/unified_agent.py as @super_agent.tool"
        }
      ]
    },
    "II": {
      "name": "Centralized Configuration",
      "violations": [
        {
          "type": "direct_os_getenv",
          "files": [
            {"path": "src/utils/helpers.py", "line": 12},
            {"path": "src/tools/web_search.py", "line": 34}
          ],
          "message": "Direct os.getenv() usage detected",
          "remediation": "Use get_settings() from src/config/settings.py"
        }
      ]
    }
  },
  "execution_time_ms": 1825,
  "files_scanned": 143
}
```

**Key fields**:
- `passed` - Overall compliance status
- `total_violations` - Count across all principles
- `principles` - Violations grouped by constitutional principle
- `files` - All file locations for each violation type
- `remediation` - Specific fix instructions

---

## Pre-commit Hook Setup

### Enable Automatic Validation

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: constitution-validator
        name: Constitution Compliance
        entry: constitution-validate
        language: python
        pass_filenames: true
        types: [python]
        stages: [commit]
```

Install hooks:

```bash
pre-commit install
```

**Behavior**: Validator runs on staged Python files before each commit. Commits are blocked if violations found.

### Temporary Bypass

When you need to commit work-in-progress:

```bash
git commit --no-verify -m "WIP: feature development"
```

**Warning**: Use sparingly. Violations must be fixed before PR merge.

---

## Common Workflows

### 1. Pre-Commit Check

**Fast incremental validation** (scans only staged files):

```bash
# Automatic via pre-commit hook
git add .
git commit -m "feat: add new feature"
# Validator runs automatically

# Manual check before committing
constitution-validate $(git diff --cached --name-only --diff-filter=ACMR | grep '\.py$')
```

**Performance**: ~1-2 seconds for typical commit (5-10 files).

### 2. Full Validation

**Complete codebase scan** (run before PRs):

```bash
constitution-validate --verbose > compliance_report.json
```

**Performance**: ~15-25 seconds for 50k LOC codebase.

### 3. Coverage Compliance Check

**Validate test coverage** against 75% minimum (Principle IV):

```bash
# Run tests with coverage first
make test-coverage

# Validator reads .coverage file
constitution-validate --check-coverage
```

**Note**: Validator reads existing `.coverage` file without re-running tests (50ms vs 30s).

### 4. Git Attribution Check

**Validate commit messages** for prohibited AI attribution (Principle VI):

```bash
# Check unpushed commits (origin/main..HEAD)
constitution-validate --check-commits

# Check last 10 commits
constitution-validate --check-commits --last-n 10
```

**Prohibited patterns detected**:
- `Co-Authored-By: Claude <noreply@anthropic.com>`
- `Generated with Claude Code`
- References to Anthropic or Claude in commit messages

---

## Ignoring False Positives

### File-Level Exclusions

Create `.constitution-ignore` in repository root:

```
# .constitution-ignore (gitignore syntax)
tests/
*.generated.py
vendor/
.venv/
migrations/alembic/versions/*.py
scripts/legacy/
```

**Pattern matching**: Uses standard gitignore glob syntax via `pathspec` library.

### Inline Suppressions

Add explanatory comments to allow specific violations:

```python
# Example: Temporary compatibility wrapper
db_client = Neo4jDriver(uri, auth)  # noqa: CONSTITUTION-III - migration compatibility
```

**Format**: `# noqa: CONSTITUTION-{PRINCIPLE_NUMBER} - {explanation}`

---

## Troubleshooting

### Error: "No .coverage file found"

**Cause**: Coverage validation attempted without running tests first.

**Fix**:
```bash
make test-coverage  # Generate .coverage file
constitution-validate --check-coverage
```

### Error: "coverage package not installed"

**Cause**: Missing dependency (should not happen with `pip install -e .[dev]`).

**Fix**:
```bash
pip install coverage>=7.0.0
```

### Error: "Constitution file not found at .specify/memory/constitution.md"

**Cause**: Missing or corrupted constitution file.

**Fix**:
```bash
git checkout .specify/memory/constitution.md  # Restore from git
```

**Note**: Validator cannot operate without the constitution source of truth (fatal error).

### Error: "git command not found"

**Cause**: Git not installed or not in PATH (for `--check-commits`).

**Fix**:
```bash
# Linux/WSL
sudo apt-get install git

# macOS
brew install git
```

### False Positives: Test Files Flagged

**Cause**: Test files legitimately use patterns that violate production code rules (e.g., `os.getenv()` in fixtures).

**Fix**: Add to `.constitution-ignore`:
```
tests/
test_*.py
*_test.py
```

### Slow Performance on Large Codebase

**Symptoms**: Validation takes >60 seconds.

**Fixes**:
1. Use incremental mode (pre-commit automatically scans only changed files)
2. Add generated/vendored code to `.constitution-ignore`
3. Enable parallel scanning (automatic, uses 4 cores)

**Expected performance**:
- 50k LOC: ~18s (full scan)
- 5 files: ~1s (incremental)

### Stale Coverage Data

**Symptoms**: Coverage violations reported for recently-added tests.

**Cause**: `.coverage` file outdated.

**Fix**:
```bash
rm .coverage
make test-coverage
constitution-validate --check-coverage
```

---

## Next Steps

- **Read the full spec**: `specs/001-constitution-validator/spec.md`
- **Understand detection logic**: `specs/001-constitution-validator/research.md`
- **Review constitutional principles**: `.specify/memory/constitution.md`
- **Integrate into CI/CD**: Add to GitHub Actions, GitLab CI, etc.

---

**Questions or Issues?** Check `docs/TROUBLESHOOTING.md` or file a GitHub issue.
