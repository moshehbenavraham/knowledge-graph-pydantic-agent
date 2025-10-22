"""Unit tests for compliance reporter module.

Tests violation grouping, remediation formatting, and report structure per US2.
"""

import pytest
from pathlib import Path
from datetime import datetime
from src.constitution_validator.models import (
    ViolationRecord,
    ViolationLocation,
    ViolationGroup,
    ComplianceReport,
    PrincipleViolationSummary,
    ConfidenceLevel,
)
from src.constitution_validator.reporter import ComplianceReporter


class TestViolationGrouping:
    """Test T034: Multiple violations of same rule are grouped with all locations listed."""

    def test_groups_violations_by_rule_id(self):
        """Test that violations with same rule_id are grouped together."""
        violations = [
            ViolationRecord(
                rule_id="CONST-II-001",
                principle_id="II",
                location=ViolationLocation(file_path=Path("src/file1.py"), line_number=10),
                message="Direct os.getenv() call",
                remediation="Use get_settings()",
                confidence=ConfidenceLevel.HIGH,
                severity="error",
            ),
            ViolationRecord(
                rule_id="CONST-II-001",
                principle_id="II",
                location=ViolationLocation(file_path=Path("src/file2.py"), line_number=20),
                message="Direct os.getenv() call",
                remediation="Use get_settings()",
                confidence=ConfidenceLevel.HIGH,
                severity="error",
            ),
            ViolationRecord(
                rule_id="CONST-I-001",
                principle_id="I",
                location=ViolationLocation(file_path=Path("src/agent_file.py"), line_number=5),
                message="Multiple agent files detected",
                remediation="Use unified_agent.py",
                confidence=ConfidenceLevel.HIGH,
                severity="error",
            ),
        ]

        reporter = ComplianceReporter()
        groups = reporter.group_violations(violations)

        # Should have 2 groups (one for CONST-II-001, one for CONST-I-001)
        assert len(groups) == 2

        # Find CONST-II-001 group
        const_ii_group = next(g for g in groups if g.rule_id == "CONST-II-001")
        assert const_ii_group.count == 2
        assert len(const_ii_group.locations) == 2

        # Find CONST-I-001 group
        const_i_group = next(g for g in groups if g.rule_id == "CONST-I-001")
        assert const_i_group.count == 1
        assert len(const_i_group.locations) == 1

    def test_group_count_matches_location_count(self):
        """Test that group count equals number of locations."""
        violations = [
            ViolationRecord(
                rule_id="CONST-II-001",
                principle_id="II",
                location=ViolationLocation(file_path=Path(f"src/file{i}.py"), line_number=i * 10),
                message="Direct os.getenv() call",
                remediation="Use get_settings()",
                confidence=ConfidenceLevel.HIGH,
                severity="error",
            )
            for i in range(1, 6)  # 5 violations
        ]

        reporter = ComplianceReporter()
        groups = reporter.group_violations(violations)

        assert len(groups) == 1
        group = groups[0]
        assert group.count == 5
        assert len(group.locations) == 5

    def test_deduplication_works(self):
        """Test that duplicate violations (same file + line) are deduplicated."""
        violations = [
            ViolationRecord(
                rule_id="CONST-II-001",
                principle_id="II",
                location=ViolationLocation(file_path=Path("src/file.py"), line_number=10),
                message="Direct os.getenv() call",
                remediation="Use get_settings()",
                confidence=ConfidenceLevel.HIGH,
                severity="error",
            ),
            # Duplicate location (should be deduplicated)
            ViolationRecord(
                rule_id="CONST-II-001",
                principle_id="II",
                location=ViolationLocation(file_path=Path("src/file.py"), line_number=10),
                message="Direct os.getenv() call",
                remediation="Use get_settings()",
                confidence=ConfidenceLevel.HIGH,
                severity="error",
            ),
            # Different line (should be kept)
            ViolationRecord(
                rule_id="CONST-II-001",
                principle_id="II",
                location=ViolationLocation(file_path=Path("src/file.py"), line_number=20),
                message="Direct os.getenv() call",
                remediation="Use get_settings()",
                confidence=ConfidenceLevel.HIGH,
                severity="error",
            ),
        ]

        reporter = ComplianceReporter()
        groups = reporter.group_violations(violations)

        assert len(groups) == 1
        group = groups[0]
        # Should have 2 unique locations (line 10 appears once, line 20 once)
        assert group.count == 2
        assert len(group.locations) == 2


class TestRemediationFormatting:
    """Test T035: Remediation includes principle quote and specific fix steps."""

    def test_remediation_includes_principle_quote(self):
        """Test that remediation message includes constitutional principle quote."""
        violation = ViolationRecord(
            rule_id="CONST-II-001",
            principle_id="II",
            location=ViolationLocation(file_path=Path("src/file.py"), line_number=10),
            message="Direct os.getenv() call",
            remediation=(
                "Principle II (Type-Safe Centralized Configuration): "
                "All configuration must use the centralized settings system.\n\n"
                "Fix: Use get_settings() from src/config/settings.py instead of os.getenv()"
            ),
            confidence=ConfidenceLevel.HIGH,
            severity="error",
        )

        # Verify remediation contains principle quote
        assert "Principle II" in violation.remediation
        assert "Type-Safe Centralized Configuration" in violation.remediation

    def test_remediation_includes_specific_fix_steps(self):
        """Test that remediation provides concrete fix instructions."""
        violation = ViolationRecord(
            rule_id="CONST-II-001",
            principle_id="II",
            location=ViolationLocation(file_path=Path("src/file.py"), line_number=10),
            message="Direct os.getenv() call",
            remediation=(
                "Principle II (Type-Safe Centralized Configuration): "
                "All configuration must use the centralized settings system.\n\n"
                "Fix: Replace os.getenv('VAR') with get_settings().var"
            ),
            confidence=ConfidenceLevel.HIGH,
            severity="error",
        )

        # Verify remediation contains specific fix instructions
        assert "Fix:" in violation.remediation
        assert "get_settings()" in violation.remediation

    def test_remediation_references_correct_constitution_section(self):
        """Test that remediation references the correct constitutional principle."""
        violations = {
            "I": "Principle I (Unified Agent Architecture)",
            "II": "Principle II (Type-Safe Centralized Configuration)",
            "III": "Principle III (Dual-Database Agentic RAG)",
            "IV": "Principle IV (Test-Driven Quality Assurance)",
            "V": "Principle V (Production-Ready Observability)",
            "VI": "Principle VI (Git Attribution & Contribution Standards)",
        }

        for principle_id, expected_text in violations.items():
            violation = ViolationRecord(
                rule_id=f"CONST-{principle_id}-001",
                principle_id=principle_id,
                location=ViolationLocation(file_path=Path("src/file.py"), line_number=10),
                message=f"Violation of principle {principle_id}",
                remediation=f"{expected_text}: Fix the issue",
                confidence=ConfidenceLevel.HIGH,
                severity="error",
            )

            assert expected_text in violation.remediation


class TestReportStructure:
    """Test T036: Report includes file paths, line numbers, principle quotes, and grouping."""

    def test_report_includes_file_paths_and_line_numbers(self):
        """Test that report includes precise file locations."""
        violations = [
            ViolationRecord(
                rule_id="CONST-II-001",
                principle_id="II",
                location=ViolationLocation(
                    file_path=Path("src/config/settings.py"),
                    line_number=45,
                    column_number=12
                ),
                message="Direct os.getenv() call",
                remediation="Use get_settings()",
                confidence=ConfidenceLevel.HIGH,
                severity="error",
            ),
        ]

        reporter = ComplianceReporter()
        report_dict = reporter.generate_report_dict(
            violations=violations,
            scanned_files=[Path("src/config/settings.py")],
            scan_duration_ms=100
        )

        # Verify file path and line number are in report
        assert len(report_dict["all_violations"]) == 1
        violation_dict = report_dict["all_violations"][0]
        assert "src/config/settings.py" in violation_dict["file"]
        assert violation_dict["line"] == 45
        assert violation_dict["column"] == 12

    def test_report_includes_principle_quotes(self):
        """Test that report includes constitutional principle information."""
        violations = [
            ViolationRecord(
                rule_id="CONST-II-001",
                principle_id="II",
                location=ViolationLocation(file_path=Path("src/file.py"), line_number=10),
                message="Direct os.getenv() call",
                remediation="Principle II: All configuration must be centralized",
                confidence=ConfidenceLevel.HIGH,
                severity="error",
            ),
        ]

        reporter = ComplianceReporter()
        report_dict = reporter.generate_report_dict(
            violations=violations,
            scanned_files=[Path("src/file.py")],
            scan_duration_ms=100
        )

        # Verify principle information is preserved in violation
        violation_dict = report_dict["all_violations"][0]
        assert "Principle II" in violation_dict["remediation"]

    def test_report_groups_violations_by_type(self):
        """Test that report groups violations by rule type."""
        violations = [
            ViolationRecord(
                rule_id="CONST-II-001",
                principle_id="II",
                location=ViolationLocation(file_path=Path(f"src/file{i}.py"), line_number=i * 10),
                message="Direct os.getenv() call",
                remediation="Use get_settings()",
                confidence=ConfidenceLevel.HIGH,
                severity="error",
            )
            for i in range(1, 4)
        ]

        reporter = ComplianceReporter()
        report_dict = reporter.generate_report_dict(
            violations=violations,
            scanned_files=[Path(f"src/file{i}.py") for i in range(1, 4)],
            scan_duration_ms=100
        )

        # Verify violations are grouped by principle
        principles = report_dict.get("violations_by_principle", [])
        assert len(principles) > 0

        # Find Principle II summary
        principle_ii = next((p for p in principles if p["principle_id"] == "II"), None)
        assert principle_ii is not None
        assert principle_ii["violation_count"] == 3

    def test_json_schema_validation(self):
        """Test that generated JSON matches expected schema structure."""
        violations = [
            ViolationRecord(
                rule_id="CONST-II-001",
                principle_id="II",
                location=ViolationLocation(file_path=Path("src/file.py"), line_number=10),
                message="Direct os.getenv() call",
                remediation="Use get_settings()",
                confidence=ConfidenceLevel.HIGH,
                severity="error",
            ),
        ]

        reporter = ComplianceReporter()
        report_dict = reporter.generate_report_dict(
            violations=violations,
            scanned_files=[Path("src/file.py")],
            scan_duration_ms=100
        )

        # Verify required top-level keys
        required_keys = [
            "report_id",
            "generated_at",
            "validator_version",
            "constitution_version",
            "scan_summary",
            "results",
            "violations_by_principle",
            "all_violations",
        ]
        for key in required_keys:
            assert key in report_dict, f"Missing required key: {key}"

        # Verify scan_summary structure
        scan_summary = report_dict["scan_summary"]
        assert "scanned_files" in scan_summary
        assert "duration_ms" in scan_summary
        assert "duration_seconds" in scan_summary

        # Verify results structure
        results = report_dict["results"]
        assert "passed" in results
        assert "total_violations" in results
        assert "error_count" in results
        assert "warning_count" in results
