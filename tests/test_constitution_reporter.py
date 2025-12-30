"""
Comprehensive tests for constitution compliance report generation.

Tests report generation, formatting, validation, and grouping functionality.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

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

# =====================================================
# FIXTURES
# =====================================================


@pytest.fixture
def sample_violation_location():
    """Sample violation location."""
    return ViolationLocation(file_path=Path("/home/user/project/src/test.py"), line_number=42)


@pytest.fixture
def sample_violation_record(sample_violation_location):
    """Sample violation record."""
    from src.constitution_validator.models import ConfidenceLevel

    return ViolationRecord(
        rule_id="CONST-I-001",
        principle_id="I",
        message="Multiple agent implementations detected",
        severity="error",
        location=sample_violation_location,
        remediation="Consolidate all agents into src/agent/unified_agent.py",
        confidence=ConfidenceLevel.HIGH,
    )


@pytest.fixture
def sample_violation_group(sample_violation_location):
    """Sample violation group."""
    return ViolationGroup(
        rule_id="CONST-I-001",
        violation_type="Multiple agent implementations",
        locations=[sample_violation_location],
        message_template="Multiple agent implementations detected",
        remediation="Consolidate all agents into src/agent/unified_agent.py",
        count=1,
    )


@pytest.fixture
def sample_principle_compliance(sample_violation_group):
    """Sample principle compliance."""
    return PrincipleViolationSummary(
        principle_id="I",
        principle_name="Unified Agent Architecture",
        compliant=False,
        violation_count=1,
        violation_groups=[sample_violation_group],
    )


@pytest.fixture
def all_principle_summaries():
    """Create all 6 principle summaries for schema validation."""
    principles = [
        ("I", "Unified Agent Architecture"),
        ("II", "Type-Safe Centralized Configuration"),
        ("III", "Dual-Database Agentic RAG"),
        ("IV", "Test-Driven Quality Assurance"),
        ("V", "Production-Ready Observability"),
        ("VI", "Git Attribution & Contribution Standards"),
    ]
    return [
        PrincipleViolationSummary(
            principle_id=pid,
            principle_name=name,
            compliant=True,
            violation_count=0,
            violation_groups=[],
        )
        for pid, name in principles
    ]


@pytest.fixture
def sample_compliance_report(sample_principle_compliance, sample_violation_record):
    """Sample compliance report."""
    return ComplianceReport(
        report_id=str(uuid4()),
        generated_at=datetime.now(UTC),
        validator_version="1.0.0",
        constitution_version="1.0.0",
        scanned_files=[Path("/home/user/project/src/test.py")],
        excluded_files=[],
        scan_duration_ms=1500,
        violations=[sample_violation_record],
        passed=False,
        error_count=1,
        warning_count=0,
        info_count=0,
        principle_summaries=[sample_principle_compliance],
        suppressed_violations=[],
        coverage_percentage=80.5,
        unpushed_commits_checked=5,
    )


@pytest.fixture
def valid_compliance_report_for_schema(sample_violation_record, sample_violation_group):
    """Sample compliance report with all 6 principles for schema validation."""
    principles = [
        ("I", "Unified Agent Architecture"),
        ("II", "Type-Safe Centralized Configuration"),
        ("III", "Dual-Database Agentic RAG"),
        ("IV", "Test-Driven Quality Assurance"),
        ("V", "Production-Ready Observability"),
        ("VI", "Git Attribution & Contribution Standards"),
    ]
    principle_summaries = []
    for idx, (pid, name) in enumerate(principles):
        if idx == 0:  # Principle I has a violation
            principle_summaries.append(
                PrincipleViolationSummary(
                    principle_id=pid,
                    principle_name=name,
                    compliant=False,
                    violation_count=1,
                    violation_groups=[sample_violation_group],
                )
            )
        else:
            principle_summaries.append(
                PrincipleViolationSummary(
                    principle_id=pid,
                    principle_name=name,
                    compliant=True,
                    violation_count=0,
                    violation_groups=[],
                )
            )
    return ComplianceReport(
        report_id=str(uuid4()),
        generated_at=datetime.now(UTC),
        validator_version="1.0.0",
        constitution_version="1.0.0",
        scanned_files=[Path("/home/user/project/src/test.py")],
        excluded_files=[],
        scan_duration_ms=1500,
        violations=[sample_violation_record],
        passed=False,
        error_count=1,
        warning_count=0,
        info_count=0,
        principle_summaries=principle_summaries,
        suppressed_violations=[],
        coverage_percentage=80.5,
        unpushed_commits_checked=5,
    )


@pytest.fixture
def compliance_reporter():
    """Compliance reporter instance."""
    return ComplianceReporter(validator_version="1.0.0", constitution_version="1.0.0")


@pytest.fixture
def report_generator():
    """Report generator instance."""
    return ReportGenerator()


# =====================================================
# JSON REPORT GENERATION TESTS
# =====================================================


def test_generate_json_report_basic(sample_compliance_report):
    """Test basic JSON report generation."""
    json_output = generate_json_report(sample_compliance_report)

    # Should be valid JSON
    report_dict = json.loads(json_output)

    assert report_dict["report_id"] == sample_compliance_report.report_id
    assert report_dict["validator_version"] == "1.0.0"
    assert report_dict["results"]["total_violations"] == 1
    assert report_dict["results"]["passed"] is False


def test_generate_json_report_with_file_output(sample_compliance_report, tmp_path):
    """Test JSON report generation with file output."""
    output_file = tmp_path / "report.json"

    json_output = generate_json_report(sample_compliance_report, output_file)

    # File should be created
    assert output_file.exists()

    # Content should match returned string
    file_content = output_file.read_text()
    assert file_content == json_output


def test_generate_json_report_formatting(sample_compliance_report):
    """Test JSON report is properly formatted."""
    json_output = generate_json_report(sample_compliance_report)

    # Should be pretty-printed with indentation
    assert "  " in json_output  # Check for 2-space indentation
    assert "\n" in json_output


def test_generate_json_report_passed_status():
    """Test JSON report for passing validation."""
    passing_report = ComplianceReport(
        report_id=str(uuid4()),
        generated_at=datetime.now(UTC),
        validator_version="1.0.0",
        constitution_version="1.0.0",
        scanned_files=[],
        excluded_files=[],
        scan_duration_ms=1000,
        passed=True,
        total_violations=0,
        error_count=0,
        warning_count=0,
        info_count=0,
        principle_summaries=[],
        suppressed_violations=[],
    )

    json_output = generate_json_report(passing_report)
    report_dict = json.loads(json_output)

    assert report_dict["results"]["passed"] is True
    assert report_dict["results"]["total_violations"] == 0


# =====================================================
# TEXT SUMMARY TESTS
# =====================================================


def test_generate_text_summary_basic(sample_compliance_report):
    """Test basic text summary generation."""
    summary = generate_text_summary(sample_compliance_report)

    assert isinstance(summary, str)
    assert len(summary) > 0


def test_generate_text_summary_contains_key_info(sample_compliance_report):
    """Test text summary contains key information."""
    summary = generate_text_summary(sample_compliance_report)

    # Should contain status
    assert "PASSED" in summary or "FAILED" in summary


# =====================================================
# DETAILED TEXT REPORT TESTS
# =====================================================


def test_generate_detailed_text_report_structure(sample_compliance_report):
    """Test detailed text report has correct structure."""
    report = generate_detailed_text_report(sample_compliance_report)

    # Check for major sections
    assert "CONSTITUTION COMPLIANCE VALIDATION REPORT" in report
    assert "SCAN SUMMARY" in report
    assert "OVERALL STATUS" in report
    assert "PRINCIPLE COMPLIANCE" in report


def test_generate_detailed_text_report_metadata(sample_compliance_report):
    """Test detailed report includes metadata."""
    report = generate_detailed_text_report(sample_compliance_report)

    assert sample_compliance_report.report_id in report
    assert "1.0.0" in report  # Validator version
    assert "Files Scanned: 1" in report


def test_generate_detailed_text_report_violation_details(sample_compliance_report):
    """Test detailed report includes violation information."""
    report = generate_detailed_text_report(sample_compliance_report)

    assert "Total Violations: 1" in report
    assert "Errors: 1" in report
    assert "Warnings: 0" in report


def test_generate_detailed_text_report_coverage_info(sample_compliance_report):
    """Test detailed report includes coverage information."""
    report = generate_detailed_text_report(sample_compliance_report)

    assert "80.5%" in report  # Coverage percentage
    assert "50.0%" in report  # Minimum required


def test_generate_detailed_text_report_git_info(sample_compliance_report):
    """Test detailed report includes git information."""
    report = generate_detailed_text_report(sample_compliance_report)

    assert "5" in report  # Commits checked


def test_generate_detailed_text_report_principle_breakdown(sample_compliance_report):
    """Test detailed report includes per-principle breakdown."""
    report = generate_detailed_text_report(sample_compliance_report)

    assert "Principle I: Unified Agent Architecture" in report
    assert "Violations: 1" in report


def test_generate_detailed_text_report_suppressed_violations():
    """Test detailed report handles suppressed violations."""
    from src.constitution_validator.models import ConfidenceLevel

    suppressed_violation = ViolationRecord(
        rule_id="CONST-I-001",
        principle_id="I",
        message="Test violation message that is long enough",
        severity="warning",
        location=ViolationLocation(file_path=Path("/test.py"), line_number=10),
        remediation="Fix this issue by addressing the root cause",
        confidence=ConfidenceLevel.HIGH,
        suppression_reason="False positive",
    )

    report_with_suppressed = ComplianceReport(
        report_id=str(uuid4()),
        generated_at=datetime.now(UTC),
        validator_version="1.0.0",
        constitution_version="1.0.0",
        scanned_files=[],
        excluded_files=[],
        scan_duration_ms=1000,
        passed=True,
        total_violations=0,
        error_count=0,
        warning_count=0,
        info_count=0,
        principle_summaries=[],
        suppressed_violations=[suppressed_violation],
    )

    report = generate_detailed_text_report(report_with_suppressed)

    assert "SUPPRESSED VIOLATIONS" in report
    assert "Total Suppressed: 1" in report
    assert "False positive" in report


def test_generate_detailed_text_report_passed_status():
    """Test detailed report for passing validation."""
    passing_report = ComplianceReport(
        report_id=str(uuid4()),
        generated_at=datetime.now(UTC),
        validator_version="1.0.0",
        constitution_version="1.0.0",
        scanned_files=[],
        excluded_files=[],
        scan_duration_ms=1000,
        passed=True,
        total_violations=0,
        error_count=0,
        warning_count=0,
        info_count=0,
        principle_summaries=[],
        suppressed_violations=[],
    )

    report = generate_detailed_text_report(passing_report)

    assert "PASSED" in report
    assert "FAILED" not in report


# =====================================================
# REPORT SCHEMA VALIDATION TESTS
# =====================================================


def test_validate_report_schema_valid(valid_compliance_report_for_schema):
    """Test schema validation with valid report."""
    report_dict = valid_compliance_report_for_schema.to_json_dict()
    is_valid, errors = validate_report_schema(report_dict)

    assert is_valid is True, f"Schema validation failed: {errors}"
    assert len(errors) == 0


def test_validate_report_schema_missing_required_keys():
    """Test schema validation with missing required keys."""
    invalid_report = {"report_id": "test"}

    is_valid, errors = validate_report_schema(invalid_report)

    assert is_valid is False
    assert len(errors) > 0
    assert "Missing required keys" in errors[0]


def test_validate_report_schema_missing_scan_summary_keys():
    """Test schema validation with incomplete scan_summary."""
    invalid_report = {
        "report_id": "test",
        "generated_at": "2024-01-01T00:00:00Z",
        "validator_version": "1.0.0",
        "constitution_version": "1.0.0",
        "scan_summary": {"scanned_files": 0},  # Missing other keys
        "results": {},
        "violations_by_principle": [],
    }

    is_valid, errors = validate_report_schema(invalid_report)

    assert is_valid is False
    assert any("scan_summary missing keys" in err for err in errors)


def test_validate_report_schema_missing_results_keys():
    """Test schema validation with incomplete results."""
    invalid_report = {
        "report_id": "test",
        "generated_at": "2024-01-01T00:00:00Z",
        "validator_version": "1.0.0",
        "constitution_version": "1.0.0",
        "scan_summary": {
            "scanned_files": 0,
            "excluded_files": 0,
            "duration_ms": 0,
            "duration_seconds": 0,
        },
        "results": {"passed": True},  # Missing other keys
        "violations_by_principle": [],
    }

    is_valid, errors = validate_report_schema(invalid_report)

    assert is_valid is False
    assert any("results missing keys" in err for err in errors)


def test_validate_report_schema_inconsistent_passed_status():
    """Test schema validation with inconsistent passed status."""
    invalid_report = {
        "report_id": "test",
        "generated_at": "2024-01-01T00:00:00Z",
        "validator_version": "1.0.0",
        "constitution_version": "1.0.0",
        "scan_summary": {
            "scanned_files": 0,
            "excluded_files": 0,
            "duration_ms": 0,
            "duration_seconds": 0,
        },
        "results": {
            "passed": True,  # Inconsistent with error_count
            "total_violations": 1,
            "error_count": 1,  # Should be 0 if passed
            "warning_count": 0,
            "info_count": 0,
        },
        "violations_by_principle": [],
    }

    is_valid, errors = validate_report_schema(invalid_report)

    assert is_valid is False
    assert any("passed but has errors" in err for err in errors)


def test_validate_report_schema_wrong_principle_count():
    """Test schema validation with wrong number of principles."""
    invalid_report = {
        "report_id": "test",
        "generated_at": "2024-01-01T00:00:00Z",
        "validator_version": "1.0.0",
        "constitution_version": "1.0.0",
        "scan_summary": {
            "scanned_files": 0,
            "excluded_files": 0,
            "duration_ms": 0,
            "duration_seconds": 0,
        },
        "results": {
            "passed": True,
            "total_violations": 0,
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
        },
        "violations_by_principle": [{"principle_id": "I"}],  # Should have 6 principles
    }

    is_valid, errors = validate_report_schema(invalid_report)

    assert is_valid is False
    assert any("Expected 6 principle summaries" in err for err in errors)


# =====================================================
# REPORT GENERATOR CLASS TESTS
# =====================================================


def test_report_generator_generate_json(report_generator, sample_compliance_report):
    """Test ReportGenerator.generate_json method."""
    json_output = report_generator.generate_json(sample_compliance_report)

    assert isinstance(json_output, str)
    report_dict = json.loads(json_output)
    assert report_dict["report_id"] == sample_compliance_report.report_id


def test_report_generator_generate_json_with_file(
    report_generator, sample_compliance_report, tmp_path
):
    """Test ReportGenerator.generate_json with file output."""
    output_file = tmp_path / "report.json"

    json_output = report_generator.generate_json(sample_compliance_report, output_file)

    assert output_file.exists()
    assert json_output == output_file.read_text()


def test_report_generator_generate_text_detailed(report_generator, sample_compliance_report):
    """Test ReportGenerator.generate_text with detailed mode."""
    text_output = report_generator.generate_text(sample_compliance_report, detailed=True)

    assert "CONSTITUTION COMPLIANCE VALIDATION REPORT" in text_output


def test_report_generator_generate_text_summary(report_generator, sample_compliance_report):
    """Test ReportGenerator.generate_text with summary mode."""
    text_output = report_generator.generate_text(sample_compliance_report, detailed=False)

    assert isinstance(text_output, str)


def test_report_generator_validate_schema(report_generator, valid_compliance_report_for_schema):
    """Test ReportGenerator.validate_schema method."""
    is_valid, errors = report_generator.validate_schema(valid_compliance_report_for_schema)

    assert is_valid is True, f"Schema validation failed: {errors}"
    assert len(errors) == 0


# =====================================================
# COMPLIANCE REPORTER CLASS TESTS
# =====================================================


def test_compliance_reporter_initialization():
    """Test ComplianceReporter initialization."""
    reporter = ComplianceReporter(validator_version="2.0.0", constitution_version="1.5.0")

    assert reporter.validator_version == "2.0.0"
    assert reporter.constitution_version == "1.5.0"


def test_compliance_reporter_group_violations(compliance_reporter, sample_violation_record):
    """Test violation grouping."""
    violations = [sample_violation_record]

    groups = compliance_reporter.group_violations(violations)

    assert len(groups) == 1
    assert groups[0].rule_id == "CONST-I-001"
    assert groups[0].count == 1


def test_compliance_reporter_group_multiple_violations(compliance_reporter):
    """Test grouping multiple violations."""
    from src.constitution_validator.models import ConfidenceLevel

    violations = [
        ViolationRecord(
            rule_id="CONST-I-001",
            principle_id="I",
            message="Violation type 1 detected in code",
            severity="error",
            location=ViolationLocation(
                file_path=Path("/test1.py"),
                line_number=10,
            ),
            remediation="Fix the issue by applying the proper pattern",
            confidence=ConfidenceLevel.HIGH,
        ),
        ViolationRecord(
            rule_id="CONST-I-001",
            principle_id="I",
            message="Violation type 1 detected in code",
            severity="error",
            location=ViolationLocation(
                file_path=Path("/test2.py"),
                line_number=20,
            ),
            remediation="Fix the issue by applying the proper pattern",
            confidence=ConfidenceLevel.HIGH,
        ),
        ViolationRecord(
            rule_id="CONST-II-001",
            principle_id="II",
            message="Violation type 2 detected in code",
            severity="warning",
            location=ViolationLocation(
                file_path=Path("/test3.py"),
                line_number=30,
            ),
            remediation="Fix by using centralized configuration",
            confidence=ConfidenceLevel.HIGH,
        ),
    ]

    groups = compliance_reporter.group_violations(violations)

    assert len(groups) == 2  # Two different rule_ids
    assert groups[0].count == 2  # Two violations for I-001
    assert groups[1].count == 1  # One violation for II-001


def test_compliance_reporter_group_violations_deduplicate_locations(compliance_reporter):
    """Test that duplicate locations are deduplicated."""
    from src.constitution_validator.models import ConfidenceLevel

    violations = [
        ViolationRecord(
            rule_id="CONST-I-001",
            principle_id="I",
            message="Violation detected in code file",
            severity="error",
            location=ViolationLocation(
                file_path=Path("/test.py"),
                line_number=10,
            ),
            remediation="Fix this by updating the code structure",
            confidence=ConfidenceLevel.HIGH,
        ),
        ViolationRecord(
            rule_id="CONST-I-001",
            principle_id="I",
            message="Violation detected in code file",
            severity="error",
            location=ViolationLocation(
                file_path=Path("/test.py"),
                line_number=10,
            ),
            remediation="Fix this by updating the code structure",
            confidence=ConfidenceLevel.HIGH,
        ),
    ]

    groups = compliance_reporter.group_violations(violations)

    assert len(groups) == 1
    assert groups[0].count == 1  # Should be deduplicated


def test_compliance_reporter_generate_report_dict(compliance_reporter, sample_violation_record):
    """Test report dictionary generation."""
    violations = [sample_violation_record]
    scanned_files = [Path("/test.py")]

    report_dict = compliance_reporter.generate_report_dict(
        violations=violations,
        scanned_files=scanned_files,
        scan_duration_ms=1500,
        coverage_percentage=85.0,
        unpushed_commits_checked=3,
    )

    assert report_dict["validator_version"] == "1.0.0"
    assert report_dict["results"]["total_violations"] == 1
    assert report_dict["results"]["error_count"] == 1
    assert report_dict["coverage"]["percentage"] == 85.0
    assert report_dict["git_attribution"]["commits_checked"] == 3


def test_compliance_reporter_generate_report_dict_passed(compliance_reporter):
    """Test report dictionary for passing validation."""
    report_dict = compliance_reporter.generate_report_dict(
        violations=[],
        scanned_files=[Path("/test.py")],
        scan_duration_ms=1000,
    )

    assert report_dict["results"]["passed"] is True
    assert report_dict["results"]["total_violations"] == 0


def test_compliance_reporter_create_principle_summaries(compliance_reporter):
    """Test creation of principle summaries."""
    from src.constitution_validator.models import ConfidenceLevel

    violations = [
        ViolationRecord(
            rule_id="CONST-I-001",
            principle_id="I",
            message="Violation for principle I detected",
            severity="error",
            location=ViolationLocation(
                file_path=Path("/test.py"),
                line_number=10,
            ),
            remediation="Fix by consolidating agent implementations",
            confidence=ConfidenceLevel.HIGH,
        ),
        ViolationRecord(
            rule_id="CONST-II-001",
            principle_id="II",
            message="Violation for principle II detected",
            severity="warning",
            location=ViolationLocation(
                file_path=Path("/test.py"),
                line_number=20,
            ),
            remediation="Fix by using centralized configuration",
            confidence=ConfidenceLevel.HIGH,
        ),
    ]

    summaries = compliance_reporter._create_principle_summaries(violations)

    # Should have all 6 principles
    assert len(summaries) == 6

    # Check principles with violations
    principle_i = next(s for s in summaries if s["principle_id"] == "I")
    assert principle_i["compliant"] is False
    assert principle_i["violation_count"] == 1

    # Check principles without violations
    principle_iii = next(s for s in summaries if s["principle_id"] == "III")
    assert principle_iii["compliant"] is True
    assert principle_iii["violation_count"] == 0
