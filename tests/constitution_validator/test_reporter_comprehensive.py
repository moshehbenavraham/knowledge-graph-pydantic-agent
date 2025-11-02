"""
Comprehensive tests for constitution_validator/reporter.py.

Tests report generation, formatting, schema validation, and compliance reporting.
Target coverage: 70%+ (up from 0.00%)
"""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from src.constitution_validator.models import (
    ComplianceReport,
    PrincipleViolationSummary,
    ViolationGroup,
    ViolationLocation,
    ViolationRecord,
)
from src.constitution_validator.reporter import (
    ComplianceReporter,
    ReportGenerator,
    generate_detailed_text_report,
    generate_json_report,
    generate_text_summary,
    validate_report_schema,
)


class TestGenerateJsonReport:
    """Test generate_json_report() function."""

    def test_generate_json_report_basic(self):
        """Test basic JSON report generation."""
        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[Path("test.py")],
            scan_duration_ms=100,
            violations=[],
            suppressed_violations=[],
            principle_summaries=[],
            passed=True,
            error_count=0,
            warning_count=0,
            info_count=0,
        )

        json_str = generate_json_report(report)

        assert json_str is not None
        assert len(json_str) > 0

        # Validate it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["validator_version"] == "1.0.0"
        assert parsed["results"]["passed"] is True

    def test_generate_json_report_with_violations(self):
        """Test JSON report generation with violations."""
        violation = ViolationRecord(
            principle_id="I",
            rule_id="CONST-I-001",
            severity="error",
            message="Test violation message",
            location=ViolationLocation(file_path=Path("test.py"), line_number=10),
            remediation="Fix this issue by following the guidelines",
            confidence="high",
        )

        summary = PrincipleViolationSummary(
            principle_id="I",
            principle_name="Test Principle",
            violation_count=1,
            violation_groups=[],
            compliant=False,
        )

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[Path("test.py")],
            scan_duration_ms=100,
            violations=[violation],
            suppressed_violations=[],
            principle_summaries=[summary],
            passed=False,
            error_count=1,
            warning_count=0,
            info_count=0,
        )

        json_str = generate_json_report(report)
        parsed = json.loads(json_str)

        assert parsed["results"]["passed"] is False
        assert parsed["results"]["error_count"] == 1
        assert len(parsed["all_violations"]) == 1

    def test_generate_json_report_to_file(self, tmp_path):
        """Test writing JSON report to file."""
        output_file = tmp_path / "report.json"

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[],
            scan_duration_ms=100,
            violations=[],
            suppressed_violations=[],
            principle_summaries=[],
            passed=True,
            error_count=0,
            warning_count=0,
            info_count=0,
        )

        json_str = generate_json_report(report, output_file)

        assert output_file.exists()
        assert output_file.read_text() == json_str


class TestGenerateTextSummary:
    """Test generate_text_summary() function."""

    def test_generate_text_summary_basic(self):
        """Test basic text summary generation."""
        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[],
            scan_duration_ms=100,
            violations=[],
            suppressed_violations=[],
            principle_summaries=[],
            passed=True,
            error_count=0,
            warning_count=0,
            info_count=0,
        )

        summary = generate_text_summary(report)

        assert summary is not None
        assert len(summary) > 0
        assert "PASSED" in summary or "passed" in summary.lower()

    def test_generate_text_summary_with_failures(self):
        """Test text summary with failures."""
        violation = ViolationRecord(
            principle_id="I",
            rule_id="CONST-I-001",
            severity="error",
            message="Test error message for validation",
            location=ViolationLocation(file_path=Path("test.py"), line_number=10),
            remediation="Fix this issue by following the guidelines",
            confidence="high",
        )

        summary_obj = PrincipleViolationSummary(
            principle_id="I",
            principle_name="Test Principle",
            violation_count=1,
            violation_groups=[],
            compliant=False,
        )

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[],
            scan_duration_ms=100,
            violations=[violation],
            suppressed_violations=[],
            principle_summaries=[summary_obj],
            passed=False,
            error_count=1,
            warning_count=0,
            info_count=0,
        )

        summary = generate_text_summary(report)

        assert "FAILED" in summary or "failed" in summary.lower()
        assert "1" in summary  # Error count


class TestGenerateDetailedTextReport:
    """Test generate_detailed_text_report() function."""

    def test_generate_detailed_report_structure(self):
        """Test detailed report has required sections."""
        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[Path("test.py")],
            scan_duration_ms=100,
            violations=[],
            suppressed_violations=[],
            principle_summaries=[],
            passed=True,
            error_count=0,
            warning_count=0,
            info_count=0,
        )

        detailed = generate_detailed_text_report(report)

        # Check for key sections
        assert "CONSTITUTION COMPLIANCE VALIDATION REPORT" in detailed
        assert "SCAN SUMMARY" in detailed
        assert "OVERALL STATUS" in detailed
        assert "PRINCIPLE COMPLIANCE" in detailed

    def test_generate_detailed_report_with_violations(self):
        """Test detailed report includes violation details."""
        violation = ViolationRecord(
            principle_id="I",
            rule_id="CONST-I-001",
            severity="error",
            message="Test violation message for detailed report",
            location=ViolationLocation(file_path=Path("test.py"), line_number=10),
            remediation="Fix the issue by addressing the violation",
            confidence="high",
        )

        group = ViolationGroup(
            rule_id="CONST-I-001",
            violation_type="test_violation",
            locations=[violation.location],
            message_template="Test violation message for detailed report",
            remediation="Fix the issue by addressing the violation",
            count=1,
        )

        summary = PrincipleViolationSummary(
            principle_id="I",
            principle_name="Unified Agent Architecture",
            violation_count=1,
            violation_groups=[group],
            compliant=False,
        )

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[Path("test.py")],
            scan_duration_ms=100,
            violations=[violation],
            suppressed_violations=[],
            principle_summaries=[summary],
            passed=False,
            error_count=1,
            warning_count=0,
            info_count=0,
        )

        detailed = generate_detailed_text_report(report)

        assert "Principle I" in detailed
        assert "Unified Agent Architecture" in detailed
        assert "test_violation" in detailed  # violation_type from ViolationGroup
        assert "Fix the issue by addressing the violation" in detailed

    def test_generate_detailed_report_with_coverage(self):
        """Test detailed report includes coverage information."""
        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[],
            scan_duration_ms=100,
            violations=[],
            suppressed_violations=[],
            principle_summaries=[],
            passed=True,
            error_count=0,
            warning_count=0,
            info_count=0,
            coverage_percentage=85.5,
        )

        detailed = generate_detailed_text_report(report)

        assert "Test Coverage" in detailed
        assert "85.5%" in detailed

    def test_generate_detailed_report_with_suppressed(self):
        """Test detailed report includes suppressed violations."""
        suppressed = ViolationRecord(
            principle_id="I",
            rule_id="CONST-I-001",
            severity="error",
            message="Suppressed violation message for testing",
            location=ViolationLocation(file_path=Path("test.py"), line_number=10),
            remediation="Not applicable in this context",
            confidence="high",
            suppressed=True,
            suppression_reason="Exception approved",
        )

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[],
            scan_duration_ms=100,
            violations=[],
            suppressed_violations=[suppressed],
            principle_summaries=[],
            passed=True,
            error_count=0,
            warning_count=0,
            info_count=0,
        )

        detailed = generate_detailed_text_report(report)

        assert "SUPPRESSED VIOLATIONS" in detailed
        assert "Exception approved" in detailed


class TestValidateReportSchema:
    """Test validate_report_schema() function."""

    def test_validate_schema_valid_report(self):
        """Test validation of valid report schema."""
        report_dict = {
            "report_id": str(uuid.uuid4()),
            "generated_at": datetime.now(UTC).isoformat(),
            "validator_version": "1.0.0",
            "constitution_version": "1.0.0",
            "scan_summary": {
                "scanned_files": 10,
                "excluded_files": 2,
                "duration_ms": 1000,
                "duration_seconds": 1.0,
            },
            "results": {
                "passed": True,
                "total_violations": 0,
                "error_count": 0,
                "warning_count": 0,
                "info_count": 0,
            },
            "violations_by_principle": [
                {
                    "principle_id": "I",
                    "principle_name": "Test",
                    "compliant": True,
                    "violation_count": 0,
                    "violation_groups": [],
                }
                for _ in range(6)
            ],
        }

        is_valid, errors = validate_report_schema(report_dict)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_schema_missing_keys(self):
        """Test validation catches missing required keys."""
        report_dict = {
            "report_id": str(uuid.uuid4()),
            # Missing required keys
        }

        is_valid, errors = validate_report_schema(report_dict)

        assert is_valid is False
        assert len(errors) > 0
        assert "Missing required keys" in errors[0]

    def test_validate_schema_invalid_principle_count(self):
        """Test validation catches wrong principle count."""
        report_dict = {
            "report_id": str(uuid.uuid4()),
            "generated_at": datetime.now(UTC).isoformat(),
            "validator_version": "1.0.0",
            "constitution_version": "1.0.0",
            "scan_summary": {
                "scanned_files": 0,
                "excluded_files": 0,
                "duration_ms": 0,
                "duration_seconds": 0.0,
            },
            "results": {
                "passed": True,
                "total_violations": 0,
                "error_count": 0,
                "warning_count": 0,
                "info_count": 0,
            },
            "violations_by_principle": [
                # Only 3 principles instead of 6
                {
                    "principle_id": "I",
                    "principle_name": "Test",
                    "compliant": True,
                    "violation_count": 0,
                    "violation_groups": [],
                }
                for _ in range(3)
            ],
        }

        is_valid, errors = validate_report_schema(report_dict)

        assert is_valid is False
        assert any("Expected 6 principle summaries" in error for error in errors)

    def test_validate_schema_passed_with_errors(self):
        """Test validation catches inconsistent passed/error state."""
        report_dict = {
            "report_id": str(uuid.uuid4()),
            "generated_at": datetime.now(UTC).isoformat(),
            "validator_version": "1.0.0",
            "constitution_version": "1.0.0",
            "scan_summary": {
                "scanned_files": 0,
                "excluded_files": 0,
                "duration_ms": 0,
                "duration_seconds": 0.0,
            },
            "results": {
                "passed": True,  # Inconsistent
                "total_violations": 5,
                "error_count": 5,  # Has errors but passed=True
                "warning_count": 0,
                "info_count": 0,
            },
            "violations_by_principle": [
                {
                    "principle_id": f"{i}",
                    "principle_name": "Test",
                    "compliant": True,
                    "violation_count": 0,
                    "violation_groups": [],
                }
                for i in range(6)
            ],
        }

        is_valid, errors = validate_report_schema(report_dict)

        assert is_valid is False
        assert any("passed but has errors" in error for error in errors)


class TestReportGenerator:
    """Test ReportGenerator class."""

    def test_report_generator_generate_json(self):
        """Test ReportGenerator.generate_json()."""
        generator = ReportGenerator()

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[],
            scan_duration_ms=100,
            violations=[],
            suppressed_violations=[],
            principle_summaries=[],
            passed=True,
            error_count=0,
            warning_count=0,
            info_count=0,
        )

        json_str = generator.generate_json(report)

        assert json_str is not None
        parsed = json.loads(json_str)
        assert parsed["validator_version"] == "1.0.0"

    def test_report_generator_generate_text_detailed(self):
        """Test ReportGenerator.generate_text() with detailed=True."""
        generator = ReportGenerator()

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[],
            scan_duration_ms=100,
            violations=[],
            suppressed_violations=[],
            principle_summaries=[],
            passed=True,
            error_count=0,
            warning_count=0,
            info_count=0,
        )

        text = generator.generate_text(report, detailed=True)

        assert "CONSTITUTION COMPLIANCE VALIDATION REPORT" in text

    def test_report_generator_generate_text_summary(self):
        """Test ReportGenerator.generate_text() with detailed=False."""
        generator = ReportGenerator()

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[],
            scan_duration_ms=100,
            violations=[],
            suppressed_violations=[],
            principle_summaries=[],
            passed=True,
            error_count=0,
            warning_count=0,
            info_count=0,
        )

        text = generator.generate_text(report, detailed=False)

        # Summary should be shorter than detailed
        assert len(text) > 0

    def test_report_generator_validate_schema(self):
        """Test ReportGenerator.validate_schema()."""
        generator = ReportGenerator()

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(UTC),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[],
            scan_duration_ms=100,
            violations=[],
            suppressed_violations=[],
            principle_summaries=[
                PrincipleViolationSummary(
                    principle_id=principle_id,
                    principle_name=f"Principle {principle_id}",
                    violation_count=0,
                    violation_groups=[],
                    compliant=True,
                )
                for principle_id in ["I", "II", "III", "IV", "V", "VI"]
            ],
            passed=True,
            error_count=0,
            warning_count=0,
            info_count=0,
        )

        is_valid, errors = generator.validate_schema(report)

        assert is_valid is True
        assert len(errors) == 0


class TestComplianceReporter:
    """Test ComplianceReporter class."""

    def test_compliance_reporter_init(self):
        """Test ComplianceReporter initialization."""
        reporter = ComplianceReporter(
            validator_version="1.0.0",
            constitution_version="1.0.0",
        )

        assert reporter.validator_version == "1.0.0"
        assert reporter.constitution_version == "1.0.0"

    def test_compliance_reporter_group_violations(self):
        """Test ComplianceReporter.group_violations()."""
        reporter = ComplianceReporter()

        violations = [
            ViolationRecord(
                principle_id="I",
                rule_id="CONST-I-001",
                severity="error",
                message="Error message one for testing",
                location=ViolationLocation(file_path=Path("test1.py"), line_number=10),
                remediation="Fix error one by updating the code",
                confidence="high",
            ),
            ViolationRecord(
                principle_id="I",
                rule_id="CONST-I-001",
                severity="error",
                message="Error message one for testing",
                location=ViolationLocation(file_path=Path("test2.py"), line_number=20),
                remediation="Fix error one by updating the code",
                confidence="high",
            ),
            ViolationRecord(
                principle_id="I",
                rule_id="CONST-I-002",
                severity="warning",
                message="Warning message one for testing",
                location=ViolationLocation(file_path=Path("test3.py"), line_number=30),
                remediation="Fix error two by updating the code",
                confidence="medium",
            ),
        ]

        groups = reporter.group_violations(violations)

        assert len(groups) == 2  # Two different rule_ids
        assert groups[0].count == 2  # CONST-I-001 has 2 violations
        assert groups[1].count == 1  # CONST-I-002 has 1 violation

    def test_compliance_reporter_group_violations_deduplication(self):
        """Test that group_violations deduplicates same file/line."""
        reporter = ComplianceReporter()

        violations = [
            ViolationRecord(
                principle_id="I",
                rule_id="CONST-I-001",
                severity="error",
                message="Error message for deduplication test",
                location=ViolationLocation(file_path=Path("test.py"), line_number=10),
                remediation="Fix this error by updating the code",
                confidence="high",
            ),
            ViolationRecord(
                principle_id="I",
                rule_id="CONST-I-001",
                severity="error",
                message="Error message for deduplication test",
                location=ViolationLocation(file_path=Path("test.py"), line_number=10),  # Duplicate
                remediation="Fix this error by updating the code",
                confidence="high",
            ),
        ]

        groups = reporter.group_violations(violations)

        assert len(groups) == 1
        assert groups[0].count == 1  # Deduplication should result in count of 1

    def test_compliance_reporter_generate_report_dict(self):
        """Test ComplianceReporter.generate_report_dict()."""
        reporter = ComplianceReporter(
            validator_version="1.0.0",
            constitution_version="1.0.0",
        )

        violations = [
            ViolationRecord(
                principle_id="I",
                rule_id="CONST-I-001",
                severity="error",
                message="Error message for report dict test",
                location=ViolationLocation(file_path=Path("test.py"), line_number=10),
                remediation="Fix this error by updating the code",
                confidence="high",
            )
        ]

        report_dict = reporter.generate_report_dict(
            violations=violations,
            scanned_files=[Path("test.py")],
            scan_duration_ms=100,
            coverage_percentage=75.0,
        )

        assert report_dict["validator_version"] == "1.0.0"
        assert report_dict["constitution_version"] == "1.0.0"
        assert report_dict["results"]["total_violations"] == 1
        assert report_dict["results"]["error_count"] == 1
        assert report_dict["results"]["passed"] is False
        assert report_dict["coverage"]["percentage"] == 75.0

    def test_compliance_reporter_generate_report_dict_passed(self):
        """Test report dict generation with no errors (passed)."""
        reporter = ComplianceReporter()

        report_dict = reporter.generate_report_dict(
            violations=[],  # No violations
            scanned_files=[],
            scan_duration_ms=100,
        )

        assert report_dict["results"]["passed"] is True
        assert report_dict["results"]["error_count"] == 0

    def test_compliance_reporter_create_principle_summaries(self):
        """Test _create_principle_summaries method."""
        reporter = ComplianceReporter()

        violations = [
            ViolationRecord(
                principle_id="I",
                rule_id="CONST-I-001",
                severity="error",
                message="Error in principle I for testing",
                location=ViolationLocation(file_path=Path("test.py"), line_number=10),
                remediation="Fix principle I by updating the code",
                confidence="high",
            ),
            ViolationRecord(
                principle_id="II",
                rule_id="CONST-II-001",
                severity="warning",
                message="Warning in principle II for testing",
                location=ViolationLocation(file_path=Path("test.py"), line_number=20),
                remediation="Fix principle II by updating the code",
                confidence="medium",
            ),
        ]

        summaries = reporter._create_principle_summaries(violations)

        # Should have 6 principles (all 6 principles must be reported)
        assert len(summaries) == 6

        # Check principle I
        principle_i = next(s for s in summaries if s["principle_id"] == "I")
        assert principle_i["compliant"] is False
        assert principle_i["violation_count"] == 1

        # Check principle II
        principle_ii = next(s for s in summaries if s["principle_id"] == "II")
        assert principle_ii["compliant"] is False
        assert principle_ii["violation_count"] == 1

        # Check principle III (should be compliant with no violations)
        principle_iii = next(s for s in summaries if s["principle_id"] == "III")
        assert principle_iii["compliant"] is True
        assert principle_iii["violation_count"] == 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_violations_list(self):
        """Test handling empty violations list."""
        reporter = ComplianceReporter()
        groups = reporter.group_violations([])
        assert groups == []

    def test_report_with_all_severity_types(self):
        """Test report with error, warning, and info violations."""
        violations = [
            ViolationRecord(
                principle_id="I",
                rule_id="CONST-I-001",
                severity="error",
                message="Error message for severity test",
                location=ViolationLocation(file_path=Path("t.py"), line_number=1),
                remediation="Fix this error by updating the code",
                confidence="high",
            ),
            ViolationRecord(
                principle_id="I",
                rule_id="CONST-I-002",
                severity="warning",
                message="Warning message for severity test",
                location=ViolationLocation(file_path=Path("t.py"), line_number=2),
                remediation="Fix this warning by updating the code",
                confidence="medium",
            ),
            ViolationRecord(
                principle_id="I",
                rule_id="CONST-I-003",
                severity="info",
                message="Info message for severity test",
                location=ViolationLocation(file_path=Path("t.py"), line_number=3),
                remediation="Fix this info by updating the code",
                confidence="low",
            ),
        ]

        reporter = ComplianceReporter()
        report_dict = reporter.generate_report_dict(
            violations=violations,
            scanned_files=[Path("t.py")],
            scan_duration_ms=100,
        )

        assert report_dict["results"]["error_count"] == 1
        assert report_dict["results"]["warning_count"] == 1
        assert report_dict["results"]["info_count"] == 1
        assert report_dict["results"]["passed"] is False  # Has errors

    def test_large_violation_list(self):
        """Test handling large number of violations."""
        # Use 500 violations to stay within 3-digit rule_id limit (001-999)
        violations = [
            ViolationRecord(
                principle_id="I",
                rule_id=f"CONST-I-{i:03d}",
                severity="error",
                message=f"Error message number {i} for large list test",
                location=ViolationLocation(file_path=Path(f"test{i}.py"), line_number=max(1, i)),
                remediation=f"Fix error number {i} by updating the code",
                confidence="high",
            )
            for i in range(1, 501)
        ]

        reporter = ComplianceReporter()
        groups = reporter.group_violations(violations)

        assert len(groups) == 500  # Each rule is unique
        assert all(g.count == 1 for g in groups)
