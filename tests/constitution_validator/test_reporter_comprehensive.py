"""
Comprehensive tests for src/constitution_validator/reporter.py.

Tests report generation for constitution compliance validation.
"""

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from src.constitution_validator.models import (
    ComplianceReport,
    ViolationGroup,
    ViolationLocation,
    ViolationRecord,
)
from src.constitution_validator.reporter import (
    generate_detailed_text_report,
    generate_json_report,
    generate_text_summary,
)


@pytest.fixture
def sample_violation_location():
    """Create sample violation location."""
    return ViolationLocation(
        file_path=Path("src/example.py"),
        line_number=42,
        column_number=10,
        context_lines=["    def example_function():", "        pass  # violation here", ""],
    )


@pytest.fixture
def sample_violation_record(sample_violation_location):
    """Create sample violation record."""
    return ViolationRecord(
        rule_id="TEST-001",
        severity="error",
        message="Test violation message",
        principle="Test Principle",
        location=sample_violation_location,
    )


@pytest.fixture
def sample_violation_group(sample_violation_record):
    """Create sample violation group."""
    return ViolationGroup(
        rule_id="TEST-001",
        principle="Test Principle",
        severity="error",
        description="Test rule description",
        violation_count=1,
        violations=[sample_violation_record],
    )


@pytest.fixture
def sample_compliance_report(sample_violation_group):
    """Create sample compliance report."""
    return ComplianceReport(
        report_id=str(uuid4()),
        generated_at=datetime.utcnow(),
        validator_version="1.0.0",
        constitution_version="1.0.0",
        scan_summary={
            "total_files": 10,
            "files_scanned": 10,
            "files_with_violations": 1,
            "scan_duration_seconds": 1.5,
        },
        total_violations=1,
        violations_by_severity={"error": 1, "warning": 0, "info": 0},
        violation_groups=[sample_violation_group],
        passed=False,
        metadata={"project": "test_project"},
    )


@pytest.fixture
def empty_compliance_report():
    """Create empty compliance report with no violations."""
    return ComplianceReport(
        report_id=str(uuid4()),
        generated_at=datetime.utcnow(),
        validator_version="1.0.0",
        constitution_version="1.0.0",
        scan_summary={
            "total_files": 10,
            "files_scanned": 10,
            "files_with_violations": 0,
            "scan_duration_seconds": 0.5,
        },
        total_violations=0,
        violations_by_severity={"error": 0, "warning": 0, "info": 0},
        violation_groups=[],
        passed=True,
        metadata={},
    )


class TestGenerateJSONReport:
    """Test JSON report generation."""

    def test_generate_json_report_basic(self, sample_compliance_report):
        """Test basic JSON report generation."""
        json_output = generate_json_report(sample_compliance_report)

        assert isinstance(json_output, str)
        assert len(json_output) > 0

        # Should be valid JSON
        parsed = json.loads(json_output)
        assert "report_id" in parsed
        assert "generated_at" in parsed
        assert "total_violations" in parsed

    def test_generate_json_report_structure(self, sample_compliance_report):
        """Test JSON report has correct structure."""
        json_output = generate_json_report(sample_compliance_report)
        report_dict = json.loads(json_output)

        assert report_dict["total_violations"] == 1
        assert report_dict["passed"] is False
        assert "scan_summary" in report_dict
        assert "violation_groups" in report_dict
        assert len(report_dict["violation_groups"]) == 1

    def test_generate_json_report_empty(self, empty_compliance_report):
        """Test JSON report for empty violations."""
        json_output = generate_json_report(empty_compliance_report)
        report_dict = json.loads(json_output)

        assert report_dict["total_violations"] == 0
        assert report_dict["passed"] is True
        assert len(report_dict["violation_groups"]) == 0

    def test_generate_json_report_with_file(self, sample_compliance_report, tmp_path):
        """Test JSON report written to file."""
        output_file = tmp_path / "report.json"

        json_output = generate_json_report(sample_compliance_report, output_file=output_file)

        assert output_file.exists()
        assert output_file.read_text() == json_output

    def test_generate_json_report_pretty_printed(self, sample_compliance_report):
        """Test JSON report is pretty-printed."""
        json_output = generate_json_report(sample_compliance_report)

        # Should have indentation (newlines and spaces)
        assert "\n" in json_output
        assert "  " in json_output

    def test_generate_json_report_unicode_safe(self):
        """Test JSON report handles unicode correctly."""
        report = ComplianceReport(
            report_id="test-123",
            generated_at=datetime.utcnow(),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scan_summary={"total_files": 1, "files_scanned": 1},
            total_violations=1,
            violations_by_severity={"error": 1},
            violation_groups=[
                ViolationGroup(
                    rule_id="TEST-001",
                    principle="Test Prínciple 日本語",
                    severity="error",
                    description="Test with unicode: ñ ü ö",
                    violation_count=0,
                    violations=[],
                )
            ],
            passed=False,
            metadata={},
        )

        json_output = generate_json_report(report)

        # Should preserve unicode characters
        assert "Prínciple" in json_output or "Pr\\u00ednciple" in json_output
        assert "日本語" in json_output or "\\u65e5\\u672c\\u8a9e" in json_output


class TestGenerateTextSummary:
    """Test text summary generation."""

    def test_generate_text_summary_basic(self, sample_compliance_report):
        """Test basic text summary generation."""
        summary = generate_text_summary(sample_compliance_report)

        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_generate_text_summary_contains_key_info(self, sample_compliance_report):
        """Test summary contains key information."""
        summary = generate_text_summary(sample_compliance_report)

        # Should contain violation count
        assert "1" in summary
        # Should contain pass/fail status
        assert "FAIL" in summary or "Failed" in summary or "❌" in summary

    def test_generate_text_summary_passed(self, empty_compliance_report):
        """Test summary for passed report."""
        summary = generate_text_summary(empty_compliance_report)

        assert "PASS" in summary or "Passed" in summary or "✅" in summary
        assert "0" in summary

    def test_generate_text_summary_not_empty(self, sample_compliance_report):
        """Test summary is not empty."""
        summary = generate_text_summary(sample_compliance_report)

        assert len(summary) > 50  # Should have substantial content


class TestGenerateDetailedTextReport:
    """Test detailed text report generation."""

    def test_generate_detailed_report_basic(self, sample_compliance_report):
        """Test basic detailed report generation."""
        report = generate_detailed_text_report(sample_compliance_report)

        assert isinstance(report, str)
        assert len(report) > 0

    def test_generate_detailed_report_structure(self, sample_compliance_report):
        """Test detailed report has correct structure."""
        report = generate_detailed_text_report(sample_compliance_report)

        # Should have header
        assert "=" * 80 in report
        assert "CONSTITUTION COMPLIANCE VALIDATION REPORT" in report

        # Should have metadata section
        assert "Report ID:" in report
        assert "Generated:" in report
        assert "Validator Version:" in report

        # Should have scan summary
        assert "SCAN SUMMARY" in report

    def test_generate_detailed_report_violations(self, sample_compliance_report):
        """Test detailed report includes violations."""
        report = generate_detailed_text_report(sample_compliance_report)

        # Should list violations
        assert "TEST-001" in report
        assert "Test violation message" in report
        assert "src/example.py" in report

    def test_generate_detailed_report_empty(self, empty_compliance_report):
        """Test detailed report for no violations."""
        report = generate_detailed_text_report(empty_compliance_report)

        # Should still have structure
        assert "CONSTITUTION COMPLIANCE VALIDATION REPORT" in report
        assert "SCAN SUMMARY" in report

        # Should indicate no violations
        assert "0" in report

    def test_generate_detailed_report_file_paths(self, sample_compliance_report):
        """Test detailed report shows file paths."""
        report = generate_detailed_text_report(sample_compliance_report)

        assert "src/example.py" in report
        assert "42" in report  # Line number

    def test_generate_detailed_report_severity_grouping(self):
        """Test report groups by severity."""
        report_with_multiple_severities = ComplianceReport(
            report_id="test-123",
            generated_at=datetime.utcnow(),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scan_summary={"total_files": 1, "files_scanned": 1},
            total_violations=3,
            violations_by_severity={"error": 1, "warning": 1, "info": 1},
            violation_groups=[
                ViolationGroup(
                    rule_id="ERR-001",
                    principle="Test",
                    severity="error",
                    description="Error",
                    violation_count=1,
                    violations=[
                        ViolationRecord(
                            rule_id="ERR-001",
                            severity="error",
                            message="Error msg",
                            principle="Test",
                            location=ViolationLocation(
                                file_path=Path("test.py"),
                                line_number=1,
                                column_number=1,
                                context_lines=[],
                            ),
                        )
                    ],
                ),
                ViolationGroup(
                    rule_id="WARN-001",
                    principle="Test",
                    severity="warning",
                    description="Warning",
                    violation_count=1,
                    violations=[
                        ViolationRecord(
                            rule_id="WARN-001",
                            severity="warning",
                            message="Warning msg",
                            principle="Test",
                            location=ViolationLocation(
                                file_path=Path("test.py"),
                                line_number=2,
                                column_number=1,
                                context_lines=[],
                            ),
                        )
                    ],
                ),
            ],
            passed=False,
            metadata={},
        )

        report = generate_detailed_text_report(report_with_multiple_severities)

        # Should show severity counts
        assert "error" in report.lower()
        assert "warning" in report.lower()

    def test_generate_detailed_report_metadata(self, sample_compliance_report):
        """Test report includes metadata."""
        report = generate_detailed_text_report(sample_compliance_report)

        assert sample_compliance_report.report_id in report
        assert sample_compliance_report.validator_version in report
        assert sample_compliance_report.constitution_version in report

    def test_generate_detailed_report_scan_metrics(self, sample_compliance_report):
        """Test report includes scan metrics."""
        report = generate_detailed_text_report(sample_compliance_report)

        # Should show file counts
        assert "10" in report  # total_files
        assert "1.5" in report or "1.50" in report  # duration

    def test_generate_detailed_report_line_breaks(self, sample_compliance_report):
        """Test report has proper line breaks."""
        report = generate_detailed_text_report(sample_compliance_report)

        # Should have multiple sections separated by newlines
        lines = report.split("\n")
        assert len(lines) > 10

    def test_generate_detailed_report_formatting(self, sample_compliance_report):
        """Test report has consistent formatting."""
        report = generate_detailed_text_report(sample_compliance_report)

        # Should have section separators
        assert "-" * 80 in report
        assert "=" * 80 in report


class TestReportGeneration_EdgeCases:
    """Test edge cases in report generation."""

    def test_report_with_very_long_message(self):
        """Test report with very long violation message."""
        long_message = "x" * 1000
        location = ViolationLocation(
            file_path=Path("test.py"), line_number=1, column_number=1, context_lines=[]
        )
        violation = ViolationRecord(
            rule_id="TEST-001",
            severity="error",
            message=long_message,
            principle="Test",
            location=location,
        )
        report = ComplianceReport(
            report_id="test",
            generated_at=datetime.utcnow(),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scan_summary={"total_files": 1, "files_scanned": 1},
            total_violations=1,
            violations_by_severity={"error": 1},
            violation_groups=[
                ViolationGroup(
                    rule_id="TEST-001",
                    principle="Test",
                    severity="error",
                    description="Test",
                    violation_count=1,
                    violations=[violation],
                )
            ],
            passed=False,
            metadata={},
        )

        # Should handle without error
        json_output = generate_json_report(report)
        text_output = generate_detailed_text_report(report)

        assert long_message in json_output
        assert len(text_output) > 0

    def test_report_with_special_characters_in_path(self):
        """Test report with special characters in file path."""
        location = ViolationLocation(
            file_path=Path("src/module with spaces/file-name_123.py"),
            line_number=1,
            column_number=1,
            context_lines=[],
        )
        violation = ViolationRecord(
            rule_id="TEST-001",
            severity="error",
            message="Test",
            principle="Test",
            location=location,
        )
        report = ComplianceReport(
            report_id="test",
            generated_at=datetime.utcnow(),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scan_summary={"total_files": 1, "files_scanned": 1},
            total_violations=1,
            violations_by_severity={"error": 1},
            violation_groups=[
                ViolationGroup(
                    rule_id="TEST-001",
                    principle="Test",
                    severity="error",
                    description="Test",
                    violation_count=1,
                    violations=[violation],
                )
            ],
            passed=False,
            metadata={},
        )

        json_output = generate_json_report(report)
        text_output = generate_detailed_text_report(report)

        assert "file-name_123.py" in json_output or "file-name_123.py" in text_output

    def test_report_with_empty_metadata(self):
        """Test report with empty metadata."""
        report = ComplianceReport(
            report_id="test",
            generated_at=datetime.utcnow(),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scan_summary={"total_files": 0, "files_scanned": 0},
            total_violations=0,
            violations_by_severity={},
            violation_groups=[],
            passed=True,
            metadata={},
        )

        json_output = generate_json_report(report)
        text_output = generate_text_summary(report)

        assert isinstance(json_output, str)
        assert isinstance(text_output, str)

    def test_json_report_invalid_output_path(self, sample_compliance_report):
        """Test JSON report with invalid output path."""
        invalid_path = Path("/nonexistent/directory/report.json")

        with pytest.raises(Exception):
            generate_json_report(sample_compliance_report, output_file=invalid_path)
