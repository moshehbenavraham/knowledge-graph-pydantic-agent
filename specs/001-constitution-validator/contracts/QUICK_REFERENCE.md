# Constitution Validator Report - Quick Reference

## Report Structure (Minimal Example)

```json
{
  "version": "1.0.0",
  "timestamp": "2025-10-21T14:30:00Z",
  "status": "PASS",
  "summary": {
    "total_violations": 0,
    "total_files_scanned": 342,
    "total_files_with_violations": 0,
    "validation_duration_ms": 12450.5,
    "principles_violated": []
  },
  "violations": [],
  "metadata": {
    "validator_version": "1.0.0",
    "python_version": "3.11.5",
    "constitution_file": "/path/to/constitution.md",
    "target_paths": [],
    "ignored_patterns": []
  }
}
```

## Exit Code → Status Mapping

| Exit Code | Status | Meaning |
|-----------|--------|---------|
| 0 | `"PASS"` | No violations found |
| Non-zero | `"FAIL"` | Violations detected |

## Violation Group Structure

```json
{
  "principle_id": "PRINCIPLE_II",
  "principle_name": "Type-Safe Centralized Configuration",
  "violation_type": "direct_os_getenv_usage",
  "violation_description": "Direct use of os.getenv() instead of centralized configuration",
  "severity": "ERROR",
  "locations": [
    {
      "file_path": "src/tools/web_search.py",
      "line_number": 42,
      "column_number": 15,
      "code_snippet": "api_key = os.getenv('BRAVE_API_KEY')",
      "context": "Found in function initialize_brave_client()"
    }
  ],
  "remediation": {
    "steps": [
      "Move configuration to src/config/settings.py",
      "Use get_settings() to access configuration values"
    ],
    "constitutional_reference": "Constitution Principle II: '...'",
    "code_example": "from src.config import get_settings\nsettings = get_settings()"
  }
}
```

## Principle IDs

| ID | Name |
|----|------|
| `PRINCIPLE_I` | Unified Agent Architecture |
| `PRINCIPLE_II` | Type-Safe Centralized Configuration |
| `PRINCIPLE_III` | Dual-Database Agentic RAG |
| `PRINCIPLE_IV` | Test-Driven Quality Assurance |
| `PRINCIPLE_V` | Production-Ready Observability |
| `PRINCIPLE_VI` | Git Attribution Standards |

## Severity Levels

| Level | Meaning | Blocking? |
|-------|---------|-----------|
| `ERROR` | Must be fixed | Yes |
| `WARNING` | Should be fixed | No |
| `INFO` | Informational | No |

## Common Violation Types

### Principle II (Configuration)
- `direct_os_getenv_usage` - Using `os.getenv()` instead of `get_settings()`
- `hardcoded_config_values` - Hardcoded secrets or config

### Principle IV (Testing)
- `insufficient_test_coverage` - Coverage below 75%
- `missing_tests` - No tests for new code

### Principle V (Observability)
- `missing_logging` - No logging in functions
- `unstructured_logging` - Not using structlog

### Principle VI (Git)
- `ai_attribution_in_commits` - AI co-author attribution
- `improper_commit_format` - Wrong commit message format

## Validation Command

```bash
# Validate a report against the schema
python validate-report.py report.json

# Expected output:
# ✓ Report is valid JSON
# ✓ Schema is valid JSON
# ✓ All 6 required fields present
# ✓ Valid status: PASS
# ✓ Status/violations consistent (violations: 0)
# ✓ Report conforms to schema
# ✓ All validation checks passed!
```

## Key Design Decisions

### 1. Group by Violation Type (Not File)
**Why?** Enables pattern recognition and bulk remediation.

**Example**: Instead of showing 3 separate violations in 3 files, show ONE violation type with 3 locations.

### 2. Include Remediation Steps
**Why?** Makes the validator a teaching tool, not just a linter.

**Example**: Each violation includes constitutional quote + fix steps + code example.

### 3. JSON-Only Output
**Why?** Machine-readable for CI/CD integration, queryable with `jq`.

**Example**: `cat report.json | jq '.summary.total_violations'`

### 4. Semantic Versioning
**Why?** Schema evolution without breaking existing tools.

**Example**: v1.1.0 adds optional fields, v2.0.0 removes fields.

## Integration Examples

### CI/CD (GitHub Actions)

```yaml
- name: Validate Constitution
  run: |
    constitution-validator --output report.json
    exit_code=$?

    # Show summary
    cat report.json | jq '.summary'

    # Upload artifact
    gh run upload report.json

    exit $exit_code
```

### Pre-Commit Hook

```bash
#!/bin/bash
constitution-validator --quiet
if [ $? -ne 0 ]; then
  echo "❌ Constitution violations detected"
  echo "Run 'constitution-validator' for details"
  exit 1
fi
```

### Python (Generate Report)

```python
import json
from datetime import datetime

report = {
    "version": "1.0.0",
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "status": "FAIL" if violations else "PASS",
    "summary": {
        "total_violations": len(violations),
        "total_files_scanned": scanned_count,
        "total_files_with_violations": len(unique_files),
        "validation_duration_ms": duration_ms,
        "principles_violated": list(set(v["principle_id"] for v in violations))
    },
    "violations": group_by_type(violations),
    "metadata": {
        "validator_version": "1.0.0",
        "python_version": "3.11.5",
        "constitution_file": str(constitution_path),
        "target_paths": target_paths,
        "ignored_patterns": ignored_patterns
    }
}

with open("report.json", "w") as f:
    json.dump(report, f, indent=2)
```

## Querying Reports with jq

```bash
# Get total violations
jq '.summary.total_violations' report.json

# Get all violated principles
jq '.summary.principles_violated[]' report.json

# Get all violation types
jq '.violations[].violation_type' report.json

# Get all affected files
jq '.violations[].locations[].file_path' report.json | sort -u

# Get ERROR severity violations only
jq '.violations[] | select(.severity == "ERROR")' report.json

# Count violations by principle
jq '[.violations[] | .principle_id] | group_by(.) | map({principle: .[0], count: length})' report.json
```

## Schema Files

- **report-schema.json** - Full JSON Schema Draft 7 definition
- **validate-report.py** - Validation utility
- **sample-pass-report.json** - Example with 0 violations
- **sample-fail-report.json** - Example with 8 violations
- **README.md** - Comprehensive documentation
- **QUICK_REFERENCE.md** - This file
