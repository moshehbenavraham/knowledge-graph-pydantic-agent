# Constitution Validator Usage Guide

Quick reference for using the Constitution Compliance Validator.

## Installation Check

```bash
# Make sure you're in the virtual environment
source .venv/bin/activate

# Verify the validator is installed
python -m src.constitution_validator.cli --version
```

## Common Commands

### 1. Quick Check (Terminal Output)

```bash
# Full codebase scan - results to terminal
python -m src.constitution_validator.cli validate

# Single file
python -m src.constitution_validator.cli validate src/agent/unified_agent.py

# Directory
python -m src.constitution_validator.cli validate src/config/
```

**Output**: JSON printed to terminal (stdout)

---

### 2. Save to File (Recommended for Analysis)

```bash
# Save JSON report to file
python -m src.constitution_validator.cli validate --output constitution_report.json

# Save text summary
python -m src.constitution_validator.cli validate --format text --output summary.txt

# Specific file with output
python -m src.constitution_validator.cli validate src/agent/base.py --output base_report.json
```

**Output**: Report saved to specified file path

---

### 3. CI/CD Mode

```bash
# Quiet mode (only counts) with file output
python -m src.constitution_validator.cli validate --quiet --output violations.json

# Check in script
python -m src.constitution_validator.cli validate --quiet --output report.json
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
  echo "❌ Constitution violations found!"
  cat report.json
  exit 1
fi
echo "✅ All checks passed!"
```

**Exit Codes**:
- `0` = Passed (no violations)
- `1` = Failed (violations found)
- `2` = Error (missing dependencies, corrupted constitution, etc.)

---

### 4. Pre-Commit Mode (Fast)

```bash
# Validate only staged files
python -m src.constitution_validator.cli validate --staged

# With file output
python -m src.constitution_validator.cli validate --staged --output staged_violations.json
```

**Speed**: <5 seconds for typical commits (only checks changed files)

---

### 5. Preview Mode

```bash
# See what would be checked without running validation
python -m src.constitution_validator.cli validate --dry-run
```

**Use when**: You want to verify which files will be scanned

---

### 6. Debugging Mode

```bash
# Verbose output with all details
python -m src.constitution_validator.cli validate --verbose --output debug_report.json
```

**Shows**: Every file checked, every rule executed, timing per principle

---

### 7. Skip Specific Checks

```bash
# Skip git commit validation (useful in non-git environments)
python -m src.constitution_validator.cli validate --skip-git

# Skip coverage measurement (if pytest-cov not configured)
python -m src.constitution_validator.cli validate --skip-coverage

# Skip both
python -m src.constitution_validator.cli validate --skip-git --skip-coverage --output report.json
```

---

## Report Output Locations

### Default (No --output flag)
- **Location**: stdout (terminal)
- **Format**: JSON by default
- **Use**: Quick checks, piping to other tools
- **Redirect**: `python -m src.constitution_validator.cli validate > report.json`

### With --output flag
- **Location**: Specified file path
- **Format**: JSON or text (via --format)
- **Use**: Saving results for later analysis
- **Examples**:
  - `--output report.json` → saves to `./report.json`
  - `--output /tmp/validation.json` → saves to `/tmp/validation.json`
  - `--output ~/reports/$(date +%Y%m%d).json` → dated reports

---

## Report Structure

JSON reports contain:

```json
{
  "report_id": "uuid",
  "generated_at": "timestamp",
  "validator_version": "1.0.0",
  "constitution_version": "1.0.0",
  "scan_summary": {
    "scanned_files": 118,
    "excluded_files": 89,
    "duration_ms": 20291,
    "duration_seconds": 20.291
  },
  "results": {
    "passed": false,
    "total_violations": 255,
    "error_count": 63,
    "warning_count": 192,
    "info_count": 0,
    "suppressed_count": 0
  },
  "coverage": {
    "percentage": 78.5,
    "meets_minimum": true
  },
  "git_attribution": {
    "commits_checked": 12
  },
  "violations_by_principle": [
    {
      "principle_id": "I",
      "principle_name": "Unified Agent Architecture",
      "compliant": false,
      "violation_count": 5,
      "violation_groups": [
        {
          "type": "violation_type",
          "count": 5,
          "message": "Description of violation",
          "remediation": "How to fix it",
          "locations": [
            "file.py:line:column",
            "..."
          ]
        }
      ]
    }
  ],
  "all_violations": [
    {
      "rule_id": "CONST-I-001",
      "principle_id": "I",
      "file": "path/to/file.py",
      "line": 42,
      "column": 8,
      "message": "Specific violation message",
      "remediation": "Fix suggestion",
      "confidence": "high",
      "severity": "error",
      "detected_code": "code snippet",
      "suggested_fix": "replacement code"
    }
  ]
}
```

---

## Inline Suppression

Suppress specific violations using comments:

```python
# Suppress a specific violation
api_key = os.getenv("API_KEY")  # noqa: CONST-II-001 - Legacy compatibility

# With reason (recommended)
client = Neo4jDriver(uri, auth)  # noqa: CONST-III-001 - Test fixture only
```

Format: `# noqa: CONST-{principle}-{number} - {reason}`

---

## Configuration Files

### .constitution-ignore

Control which files are excluded from validation:

```gitignore
# Third-party code
vendor/
third_party/

# Generated files
*_pb2.py
*.generated.py

# Specific patterns for specific rules
tests/fixtures/**/*.py  # Test data
```

Location: Repository root (`.constitution-ignore`)

### Constitution File

The validator reads principles from:

```
.specify/memory/constitution.md
```

This file defines all 6 constitutional principles. **Do not modify** unless updating the constitution.

---

## Integration Examples

### GitHub Actions

```yaml
- name: Constitution Validation
  run: |
    source .venv/bin/activate
    python -m src.constitution_validator.cli validate --quiet --output constitution_report.json

- name: Upload Report
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: constitution-report
    path: constitution_report.json
```

### Pre-Commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: constitution-validator
        name: Constitution Compliance Check
        entry: python -m src.constitution_validator.cli validate --staged
        language: system
        pass_filenames: false
        always_run: true
```

### Makefile Integration

```makefile
.PHONY: validate-constitution
validate-constitution:
	@echo "Running constitution validation..."
	python -m src.constitution_validator.cli validate --output constitution_report.json
	@echo "Report saved to constitution_report.json"

.PHONY: validate-quick
validate-quick:
	python -m src.constitution_validator.cli validate --skip-coverage --skip-git --quiet
```

---

## Troubleshooting

### "Constitution file not found"
- Ensure you're in the repository root
- Check that `.specify/memory/constitution.md` exists

### "pytest-cov not found" warning
- Install: `pip install pytest-cov`
- Or skip coverage: `--skip-coverage`

### "Could not parse coverage"
- Coverage measurement requires pytest-cov configuration
- Use `--skip-coverage` to bypass this check
- Configure `.coveragerc` for accurate measurements

### Slow validation (>30s)
- Use `--staged` for incremental validation
- Use `--skip-coverage` (coverage measurement takes ~13s)
- Check `.constitution-ignore` to exclude unnecessary files

---

## Performance Tips

1. **Pre-commit mode**: Use `--staged` for fast validation (<5s typically)
2. **Skip expensive checks**: Use `--skip-coverage` in development
3. **Ignore patterns**: Add patterns to `.constitution-ignore` to exclude files
4. **Specific paths**: Validate only changed files/directories

---

## Need Help?

```bash
# General help
python -m src.constitution_validator.cli --help

# Command-specific help
python -m src.constitution_validator.cli validate --help

# Version info
python -m src.constitution_validator.cli --version
```
