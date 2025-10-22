# Constitution Validator Report Contract

This directory contains the JSON schema contract for the Constitution Compliance Validator CLI output format.

## Files

- **report-schema.json** - JSON Schema Draft 7 definition for validator output
- **validate-report.py** - Validation utility to check reports against schema
- **sample-pass-report.json** - Example report with zero violations (exit 0)
- **sample-fail-report.json** - Example report with violations (exit non-zero)

## Schema Overview

The report schema defines a structured JSON format with the following key sections:

### 1. Top-Level Structure

```json
{
  "version": "1.0.0",              // Schema version (semver)
  "timestamp": "2025-10-21T...",   // ISO 8601 validation timestamp
  "status": "PASS | FAIL",         // Overall result
  "summary": { ... },              // Statistics
  "violations": [ ... ],           // Grouped violations
  "metadata": { ... }              // Environment context
}
```

### 2. Summary Statistics

The `summary` object provides high-level metrics:

- `total_violations`: Total count of violation instances
- `total_files_scanned`: Number of files analyzed
- `total_files_with_violations`: Unique files containing violations
- `validation_duration_ms`: Execution time in milliseconds
- `principles_violated`: Array of principle IDs with violations

### 3. Violation Groups

Violations are **grouped by type** (not by file). Each violation group contains:

- **Principle identification**: `principle_id`, `principle_name`
- **Violation type**: Specific rule violated (e.g., `direct_os_getenv_usage`)
- **Description**: Human-readable explanation
- **Severity**: `ERROR`, `WARNING`, or `INFO`
- **Locations**: Array of all file paths where this violation occurs
- **Remediation**: Actionable fix steps and constitutional references

### 4. Violation Locations

Each location within a violation group specifies:

- `file_path`: Relative path from repo root
- `line_number`: Line where violation occurs (0 if not line-specific)
- `column_number`: Optional column position
- `code_snippet`: Optional excerpt of offending code
- `context`: Optional additional details

### 5. Metadata

Provides validation environment context:

- `validator_version`: Tool version
- `python_version`: Python interpreter version
- `constitution_file`: Path to constitution source
- `target_paths`: Specific paths validated (empty = full codebase)
- `ignored_patterns`: Exclusion patterns from `.constitution-ignore`
- `cli_flags`: Optional flags used (verbose, quiet, dry_run)

## Exit Code Mapping

The validator uses standard exit codes:

- **0** → `"status": "PASS"` - No violations detected
- **Non-zero** → `"status": "FAIL"` - Violations detected

The status field MUST be consistent with violation counts:
- `PASS` requires `total_violations: 0`
- `FAIL` requires `total_violations > 0`

## Violation Grouping

**Critical Design Decision**: Violations are grouped by **type**, not by file.

### Why Group by Type?

1. **Actionable Remediation**: Developers can fix all instances of a violation type with a single approach
2. **Pattern Recognition**: Makes systemic issues immediately visible (e.g., 15 `os.getenv()` calls across codebase)
3. **Constitutional Teaching**: Each group includes the relevant constitutional principle quote
4. **Efficient Remediation**: Fix all locations of one violation type before moving to the next

### Example Structure

```json
{
  "violations": [
    {
      "violation_type": "direct_os_getenv_usage",
      "locations": [
        {"file_path": "src/tools/web_search.py", "line_number": 42},
        {"file_path": "src/agent/custom_tool.py", "line_number": 156},
        {"file_path": "tests/test_integration.py", "line_number": 89}
      ],
      "remediation": {
        "steps": [
          "Move configuration to src/config/settings.py",
          "Use get_settings() to access configuration values"
        ]
      }
    }
  ]
}
```

## Constitutional Principles Mapping

The schema supports all six constitutional principles:

| Principle ID | Principle Name | Example Violation Types |
|--------------|----------------|-------------------------|
| `PRINCIPLE_I` | Unified Agent Architecture | `multiple_agent_files`, `agent_outside_unified_agent_py` |
| `PRINCIPLE_II` | Type-Safe Centralized Configuration | `direct_os_getenv_usage`, `hardcoded_config_values` |
| `PRINCIPLE_III` | Dual-Database Agentic RAG | `missing_postgresql_client`, `missing_neo4j_client`, `database_bypass` |
| `PRINCIPLE_IV` | Test-Driven Quality Assurance | `insufficient_test_coverage`, `missing_tests` |
| `PRINCIPLE_V` | Production-Ready Observability | `missing_logging`, `missing_metrics`, `unstructured_logging` |
| `PRINCIPLE_VI` | Git Attribution Standards | `ai_attribution_in_commits`, `improper_commit_format` |

## Validation Usage

### Validating Reports

```bash
# Basic validation (requires jsonschema: pip install jsonschema)
python validate-report.py path/to/report.json

# Example output for valid report:
# Loading report: report.json
# ✓ Report is valid JSON
# ✓ Schema is valid JSON
# ✓ All 6 required fields present
# ✓ Valid status: FAIL
# ✓ Status/violations consistent (violations: 8)
# ✓ Report conforms to schema
# ✓ All validation checks passed!
```

### Testing Schema Changes

When modifying the schema:

1. Update `report-schema.json`
2. Validate schema syntax: `python -c "import json; json.load(open('report-schema.json'))"`
3. Update sample reports if needed
4. Run validation tests: `python validate-report.py sample-pass-report.json`
5. Update schema `version` field if breaking changes

## Schema Versioning

The schema follows semantic versioning in the `version` field:

- **Major** (1.0.0 → 2.0.0): Breaking changes to structure (remove/rename fields)
- **Minor** (1.0.0 → 1.1.0): Backwards-compatible additions (new optional fields)
- **Patch** (1.0.0 → 1.0.1): Non-functional changes (documentation, examples)

Current version: **1.0.0**

## Integration Example

### Python (Validator Implementation)

```python
from datetime import datetime
from pathlib import Path
import json

def generate_report(violations: list, scanned_files: int, duration_ms: float) -> dict:
    """Generate compliant JSON report."""
    return {
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "FAIL" if violations else "PASS",
        "summary": {
            "total_violations": len(violations),
            "total_files_scanned": scanned_files,
            "total_files_with_violations": len(set(v["file_path"] for v in violations)),
            "validation_duration_ms": duration_ms,
            "principles_violated": list(set(v["principle_id"] for v in violations))
        },
        "violations": group_violations_by_type(violations),
        "metadata": {
            "validator_version": "1.0.0",
            "python_version": sys.version.split()[0],
            "constitution_file": str(Path(".specify/memory/constitution.md").resolve()),
            "target_paths": [],
            "ignored_patterns": load_ignore_patterns()
        }
    }
```

### CI/CD Integration (GitHub Actions)

```yaml
- name: Validate Constitution Compliance
  run: |
    constitution-validator --output report.json
    exit_code=$?

    # Upload report artifact
    cat report.json | jq .

    # Fail workflow if violations found
    exit $exit_code
```

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

constitution-validator --quiet --output /tmp/constitution-report.json
if [ $? -ne 0 ]; then
  echo "❌ Constitution compliance violations detected"
  echo "Run 'constitution-validator' for detailed report"
  exit 1
fi
```

## Future Considerations

Potential schema enhancements for future versions:

- **Diff Mode**: Include `previous_report` field to show new vs. existing violations
- **Auto-Fix Suggestions**: Machine-readable fix instructions for automated remediation
- **Severity Overrides**: Allow configuration-based severity customization
- **Historical Tracking**: Link to violation history database for trend analysis
- **Multi-Repository Support**: Aggregate reports across multiple repositories

## Related Documentation

- Feature Specification: `../spec.md`
- Implementation Plan: `../plan.md`
- Data Model: `../data-model.md` (to be generated)
- Quickstart Guide: `../quickstart.md` (to be generated)
