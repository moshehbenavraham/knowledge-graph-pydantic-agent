#!/usr/bin/env python3
"""
Validation utility for Constitution Compliance Validator report output.

Usage:
    python validate-report.py report.json

This script validates that a JSON report file conforms to the report-schema.json
contract. Useful for testing the validator's output format during development.
"""

import json
import sys
from pathlib import Path


def validate_report(report_path: Path, schema_path: Path) -> bool:
    """
    Validate a report JSON file against the schema.

    Args:
        report_path: Path to the report JSON file to validate
        schema_path: Path to the JSON schema file

    Returns:
        True if valid, False otherwise
    """
    try:
        # Try importing jsonschema (optional dependency for validation)
        try:
            from jsonschema import validate
            from jsonschema.exceptions import ValidationError

            use_jsonschema = True
        except ImportError:
            print("⚠️  Warning: jsonschema not installed, performing basic validation only")
            print("   Install with: pip install jsonschema")
            use_jsonschema = False

        # Load report
        print(f"Loading report: {report_path}")
        with open(report_path) as f:
            report = json.load(f)
        print("✓ Report is valid JSON")

        # Load schema
        print(f"Loading schema: {schema_path}")
        with open(schema_path) as f:
            schema = json.load(f)
        print("✓ Schema is valid JSON")

        # Basic validation (always performed)
        print("\nPerforming basic validation...")
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in report:
                print(f"✗ Missing required field: {field}")
                return False
        print(f"✓ All {len(required_fields)} required fields present")

        # Check status field
        status = report.get("status")
        if status not in ["PASS", "FAIL"]:
            print(f"✗ Invalid status: {status} (must be PASS or FAIL)")
            return False
        print(f"✓ Valid status: {status}")

        # Check summary statistics
        summary = report.get("summary", {})
        total_violations = summary.get("total_violations", 0)
        if status == "PASS" and total_violations > 0:
            print(f"✗ Inconsistency: status=PASS but total_violations={total_violations}")
            return False
        if status == "FAIL" and total_violations == 0:
            print("✗ Inconsistency: status=FAIL but total_violations=0")
            return False
        print(f"✓ Status/violations consistent (violations: {total_violations})")

        # Full schema validation (if jsonschema available)
        if use_jsonschema:
            print("\nPerforming full schema validation...")
            try:
                validate(instance=report, schema=schema)
                print("✓ Report conforms to schema")
            except ValidationError as e:
                print(f"✗ Schema validation failed: {e.message}")
                print(f"   Path: {' -> '.join(str(p) for p in e.path)}")
                return False

        print("\n✓ All validation checks passed!")
        return True

    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON: {e}")
        return False
    except FileNotFoundError as e:
        print(f"✗ File not found: {e}")
        return False
    except Exception as e:
        print(f"✗ Validation error: {e}")
        return False


def main():
    """CLI entry point."""
    if len(sys.argv) != 2:
        print("Usage: python validate-report.py <report.json>")
        print("\nValidates a Constitution Compliance Validator report against the schema.")
        sys.exit(1)

    report_path = Path(sys.argv[1])
    schema_path = Path(__file__).parent / "report-schema.json"

    if not report_path.exists():
        print(f"Error: Report file not found: {report_path}")
        sys.exit(1)

    if not schema_path.exists():
        print(f"Error: Schema file not found: {schema_path}")
        sys.exit(1)

    success = validate_report(report_path, schema_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
