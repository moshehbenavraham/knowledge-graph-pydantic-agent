"""
Report generation for constitution compliance validation.

Converts ComplianceReport objects to JSON and human-readable formats.
"""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from .models import (
    ComplianceReport,
    ViolationGroup,
    ViolationLocation,
    ViolationRecord,
)

logger = structlog.get_logger(__name__)


def generate_json_report(report: ComplianceReport, output_file: Path | None = None) -> str:
    """
    Generate JSON report from ComplianceReport.

    Args:
        report: ComplianceReport instance
        output_file: Optional path to write JSON file

    Returns:
        JSON string representation of report
    """
    logger.info("Generating JSON report", report_id=report.report_id)

    # Use the model's built-in to_json_dict() method
    report_dict = report.to_json_dict()

    # Pretty-print JSON with 2-space indentation
    json_output = json.dumps(report_dict, indent=2, ensure_ascii=False)

    # Optionally write to file
    if output_file:
        output_file.write_text(json_output, encoding="utf-8")
        logger.info("JSON report written to file", file=str(output_file))

    logger.info(
        "JSON report generated",
        size_bytes=len(json_output),
        violations=report.total_violations,
        passed=report.passed,
    )

    return json_output


def generate_text_summary(report: ComplianceReport) -> str:
    """
    Generate human-readable text summary from ComplianceReport.

    Args:
        report: ComplianceReport instance

    Returns:
        Formatted text summary
    """
    logger.debug("Generating text summary", report_id=report.report_id)
    # Use the model's built-in print_summary() method
    summary = report.print_summary()
    logger.debug("Text summary generated", length=len(summary))
    return summary


def generate_detailed_text_report(report: ComplianceReport) -> str:
    """
    Generate detailed human-readable report with all violation locations.

    Args:
        report: ComplianceReport instance

    Returns:
        Detailed formatted text report
    """
    logger.info(
        "Generating detailed text report",
        report_id=report.report_id,
        violations=report.total_violations,
        passed=report.passed,
    )

    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("CONSTITUTION COMPLIANCE VALIDATION REPORT")
    lines.append("=" * 80)
    lines.append("")

    # Metadata
    lines.append(f"Report ID: {report.report_id}")
    lines.append(f"Generated: {report.generated_at.isoformat()}")
    lines.append(f"Validator Version: {report.validator_version}")
    lines.append(f"Constitution Version: {report.constitution_version}")
    lines.append("")

    # Scan Summary
    lines.append("SCAN SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Files Scanned: {len(report.scanned_files)}")
    lines.append(f"Files Excluded: {len(report.excluded_files)}")
    lines.append(f"Duration: {report.scan_duration_seconds:.2f}s")
    lines.append("")

    # Overall Status
    status = "✓ PASSED" if report.passed else "✗ FAILED"
    lines.append(f"OVERALL STATUS: {status}")
    lines.append("-" * 80)
    lines.append(f"Total Violations: {report.total_violations}")
    lines.append(f"  - Errors: {report.error_count}")
    lines.append(f"  - Warnings: {report.warning_count}")
    lines.append(f"  - Info: {report.info_count}")
    lines.append(f"Suppressed: {len(report.suppressed_violations)}")
    lines.append("")

    # Coverage Info (if available)
    if report.coverage_percentage is not None:
        meets_min = report.coverage_percentage >= 75.0
        status_icon = "✓" if meets_min else "✗"
        lines.append(f"Test Coverage: {status_icon} {report.coverage_percentage:.1f}%")
        lines.append("  Minimum Required: 75.0%")
        lines.append("")

    # Git Attribution (if available)
    if report.unpushed_commits_checked is not None:
        lines.append(f"Git Commits Checked: {report.unpushed_commits_checked}")
        lines.append("")

    # Per-Principle Results
    lines.append("PRINCIPLE COMPLIANCE")
    lines.append("=" * 80)
    lines.append("")

    for summary in report.principle_summaries:
        status_icon = "✓" if summary.compliant else "✗"
        lines.append(f"{status_icon} Principle {summary.principle_id}: {summary.principle_name}")
        lines.append(f"  Violations: {summary.violation_count}")
        lines.append("")

        if summary.violation_groups:
            for group in summary.violation_groups:
                lines.append(f"  • {group.violation_type} ({group.count} occurrences)")
                lines.append(f"    Message: {group.message_template}")
                lines.append(f"    Fix: {group.remediation}")
                lines.append("")

                # List all locations
                lines.append("    Locations:")
                for loc in group.locations:
                    lines.append(f"      - {loc}")
                lines.append("")

    # Suppressed Violations (if any)
    if report.suppressed_violations:
        lines.append("SUPPRESSED VIOLATIONS")
        lines.append("=" * 80)
        lines.append(f"Total Suppressed: {len(report.suppressed_violations)}")
        lines.append("")

        for violation in report.suppressed_violations:
            lines.append(f"  • {violation.location}")
            lines.append(f"    Rule: {violation.rule_id}")
            lines.append(f"    Message: {violation.message}")
            lines.append(f"    Reason: {violation.suppression_reason}")
            lines.append("")

    # Footer
    lines.append("=" * 80)
    if report.passed:
        lines.append("✓ Constitution compliance check PASSED")
    else:
        lines.append("✗ Constitution compliance check FAILED")
        lines.append(f"  Fix {report.error_count} error(s) before proceeding")
    lines.append("=" * 80)

    text_report = "\n".join(lines)
    logger.info("Detailed text report generated", length=len(text_report), lines=len(lines))
    return text_report


def validate_report_schema(report_dict: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate report structure matches expected schema.

    Args:
        report_dict: Report dictionary from to_json_dict()

    Returns:
        Tuple of (is_valid, errors)
    """
    logger.debug("Validating report schema")
    errors = []

    # Required top-level keys
    required_keys = {
        "report_id",
        "generated_at",
        "validator_version",
        "constitution_version",
        "scan_summary",
        "results",
        "violations_by_principle",
    }

    missing_keys = required_keys - set(report_dict.keys())
    if missing_keys:
        errors.append(f"Missing required keys: {missing_keys}")

    # Validate scan_summary structure
    if "scan_summary" in report_dict:
        scan_summary = report_dict["scan_summary"]
        required_scan_keys = {"scanned_files", "excluded_files", "duration_ms", "duration_seconds"}
        missing = required_scan_keys - set(scan_summary.keys())
        if missing:
            errors.append(f"scan_summary missing keys: {missing}")

    # Validate results structure
    if "results" in report_dict:
        results = report_dict["results"]
        required_result_keys = {
            "passed",
            "total_violations",
            "error_count",
            "warning_count",
            "info_count",
        }
        missing = required_result_keys - set(results.keys())
        if missing:
            errors.append(f"results missing keys: {missing}")

        # Validate passed status matches error count
        if results.get("passed") and results.get("error_count", 0) > 0:
            errors.append("Report marked as passed but has errors")

    # Validate violations_by_principle is a list
    if "violations_by_principle" in report_dict:
        if not isinstance(report_dict["violations_by_principle"], list):
            errors.append("violations_by_principle must be a list")
        elif len(report_dict["violations_by_principle"]) != 6:
            errors.append(
                f"Expected 6 principle summaries, got {len(report_dict['violations_by_principle'])}"
            )

    is_valid = len(errors) == 0

    if is_valid:
        logger.debug("Report schema validation passed")
    else:
        logger.warning("Report schema validation failed", errors=errors)

    return is_valid, errors


class ReportGenerator:
    """
    Report generator for constitution compliance validation.

    Provides unified interface for generating JSON and text reports.
    """

    def generate_json(self, report: ComplianceReport, output_file: Path | None = None) -> str:
        """
        Generate JSON report.

        Args:
            report: Compliance report to format
            output_file: Optional file to write to

        Returns:
            JSON string
        """
        logger.debug(
            "ReportGenerator.generate_json called",
            report_id=report.report_id,
            has_output_file=output_file is not None,
        )
        return generate_json_report(report, output_file)

    def generate_text(self, report: ComplianceReport, detailed: bool = True) -> str:
        """
        Generate text report.

        Args:
            report: Compliance report to format
            detailed: Include detailed violation information (default True)

        Returns:
            Formatted text string
        """
        logger.debug(
            "ReportGenerator.generate_text called", report_id=report.report_id, detailed=detailed
        )
        if detailed:
            return generate_detailed_text_report(report)
        return generate_text_summary(report)

    def validate_schema(self, report: ComplianceReport) -> tuple[bool, list[str]]:
        """
        Validate report matches expected schema.

        Args:
            report: Compliance report to validate

        Returns:
            Tuple of (is_valid, errors)
        """
        report_dict = report.to_json_dict()
        return validate_report_schema(report_dict)


class ComplianceReporter:
    """
    Compliance reporter for grouping violations and generating reports.

    Used by tests and CLI to process validation results.
    """

    def __init__(self, validator_version: str = "1.0.0", constitution_version: str = "1.0.0"):
        """
        Initialize compliance reporter.

        Args:
            validator_version: Version of validator
            constitution_version: Version of constitution
        """
        logger.debug(
            "Initializing ComplianceReporter",
            validator_version=validator_version,
            constitution_version=constitution_version,
        )
        self.validator_version = validator_version
        self.constitution_version = constitution_version

    def group_violations(self, violations: list[ViolationRecord]) -> list[ViolationGroup]:
        """
        Group violations by rule_id and deduplicate locations.

        Args:
            violations: List of violation records

        Returns:
            List of violation groups
        """
        logger.debug("Grouping violations", count=len(violations))

        # Group by rule_id
        groups_dict: dict[str, list[ViolationRecord]] = {}
        for violation in violations:
            if violation.rule_id not in groups_dict:
                groups_dict[violation.rule_id] = []
            groups_dict[violation.rule_id].append(violation)

        # Create ViolationGroup objects with deduplicated locations
        groups = []
        for rule_id, rule_violations in groups_dict.items():
            # Deduplicate locations by file path and line number
            unique_locations: dict[tuple, ViolationLocation] = {}
            for v in rule_violations:
                location_key = (str(v.location.file_path), v.location.line_number)
                if location_key not in unique_locations:
                    unique_locations[location_key] = v.location

            # Use first violation for template message and remediation
            first_violation = rule_violations[0]

            group = ViolationGroup(
                rule_id=rule_id,
                violation_type=first_violation.message,
                locations=list(unique_locations.values()),
                message_template=first_violation.message,
                remediation=first_violation.remediation,
                count=len(unique_locations),
            )
            groups.append(group)

        logger.debug("Violations grouped", group_count=len(groups))
        return groups

    def generate_report_dict(
        self,
        violations: list[ViolationRecord],
        scanned_files: list[Path],
        scan_duration_ms: int,
        excluded_files: list[Path] | None = None,
        suppressed_violations: list[ViolationRecord] | None = None,
        coverage_percentage: float | None = None,
        unpushed_commits_checked: int | None = None,
    ) -> dict[str, Any]:
        """
        Generate report dictionary from violations.

        Args:
            violations: List of violations
            scanned_files: Files that were scanned
            scan_duration_ms: Scan duration in milliseconds
            excluded_files: Files that were excluded
            suppressed_violations: Suppressed violations
            coverage_percentage: Test coverage percentage
            unpushed_commits_checked: Number of git commits checked

        Returns:
            Report dictionary matching schema
        """
        logger.info(
            "Generating compliance report",
            violations=len(violations),
            scanned_files=len(scanned_files),
        )

        # Group violations by principle
        principle_summaries = self._create_principle_summaries(violations)

        # Calculate counts by severity
        error_count = sum(1 for v in violations if v.severity == "error")
        warning_count = sum(1 for v in violations if v.severity == "warning")
        info_count = sum(1 for v in violations if v.severity == "info")

        # Build report dictionary
        report_dict: dict[str, Any] = {
            "report_id": str(uuid.uuid4()),
            "generated_at": datetime.now(UTC).isoformat() + "Z",
            "validator_version": self.validator_version,
            "constitution_version": self.constitution_version,
            "scan_summary": {
                "scanned_files": len(scanned_files),
                "excluded_files": len(excluded_files or []),
                "duration_ms": scan_duration_ms,
                "duration_seconds": scan_duration_ms / 1000.0,
            },
            "results": {
                "passed": error_count == 0,
                "total_violations": len(violations),
                "error_count": error_count,
                "warning_count": warning_count,
                "info_count": info_count,
                "suppressed_count": len(suppressed_violations or []),
            },
            "coverage": {
                "percentage": coverage_percentage,
                "meets_minimum": coverage_percentage >= 75.0 if coverage_percentage else None,
            },
            "git_attribution": {"commits_checked": unpushed_commits_checked},
            "violations_by_principle": [
                {
                    "principle_id": summary["principle_id"],
                    "principle_name": summary["principle_name"],
                    "compliant": summary["compliant"],
                    "violation_count": summary["violation_count"],
                    "violation_groups": [
                        {
                            "type": group["type"],
                            "count": group["count"],
                            "message": group["message"],
                            "remediation": group["remediation"],
                            "locations": group["locations"],
                        }
                        for group in summary["violation_groups"]
                    ],
                }
                for summary in principle_summaries
            ],
            "all_violations": [v.to_dict() for v in violations],
        }

        logger.info(
            "Compliance report generated",
            passed=report_dict["results"]["passed"],
            total_violations=len(violations),
        )

        return report_dict

    def _create_principle_summaries(
        self, violations: list[ViolationRecord]
    ) -> list[dict[str, Any]]:
        """
        Create per-principle summaries with grouped violations.

        Args:
            violations: List of violations

        Returns:
            List of principle summary dicts
        """
        # Define all 6 principles
        principles = {
            "I": "Unified Agent Architecture",
            "II": "Type-Safe Centralized Configuration",
            "III": "Dual-Database Agentic RAG",
            "IV": "Test-Driven Quality Assurance",
            "V": "Production-Ready Observability",
            "VI": "Git Attribution & Contribution Standards",
        }

        summaries = []
        for principle_id, principle_name in principles.items():
            # Filter violations for this principle
            principle_violations = [v for v in violations if v.principle_id == principle_id]

            # Group violations
            groups = self.group_violations(principle_violations)

            summary = {
                "principle_id": principle_id,
                "principle_name": principle_name,
                "compliant": len(principle_violations) == 0,
                "violation_count": len(principle_violations),
                "violation_groups": [
                    {
                        "type": group.violation_type,
                        "count": group.count,
                        "message": group.message_template,
                        "remediation": group.remediation,
                        "locations": [str(loc) for loc in group.locations],
                    }
                    for group in groups
                ],
            }
            summaries.append(summary)

        return summaries
