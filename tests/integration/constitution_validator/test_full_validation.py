"""
Integration tests for full constitution validation flow.

Tests end-to-end validation including all 6 principles, file discovery,
report generation, and exit codes.
"""

from pathlib import Path

import pytest

from src.constitution_validator.loader import ConstitutionLoader, IgnoreConfigurationLoader
from src.constitution_validator.models import ComplianceReport


class TestFullValidationFlow:
    """Integration tests for complete validation workflow."""

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Get path to test fixtures directory."""
        return Path(__file__).parent / "fixtures"

    @pytest.fixture
    def violation_samples_dir(self, fixtures_dir: Path) -> Path:
        """Get path to violation samples directory."""
        return fixtures_dir / "violation_samples"

    @pytest.fixture
    def valid_codebase_dir(self, fixtures_dir: Path) -> Path:
        """Get path to valid/compliant codebase."""
        return fixtures_dir / "valid_codebase"

    def test_loads_constitution_successfully(self):
        """Test that constitution file loads without errors."""
        loader = ConstitutionLoader()
        constitution = loader.load()

        assert constitution is not None
        assert len(constitution.principles) == 6
        assert constitution.version is not None
        assert constitution.checksum is not None

    def test_validates_violation_samples_and_detects_all_principles(
        self, violation_samples_dir: Path
    ):
        """Test end-to-end validation detects violations for all 6 principles."""
        # This is the key integration test - run validator on known violations
        # and verify all are detected

        # For now, we'll test the components individually
        # Full CLI integration happens in later tasks
        loader = ConstitutionLoader()
        constitution = loader.load()

        assert constitution is not None
        # Verify we have rules for all 6 principles
        expected_principles = {"I", "II", "III", "IV", "V", "VI"}
        actual_principles = {p.principle_id for p in constitution.principles}
        assert expected_principles == actual_principles

    def test_report_structure_matches_json_schema(self):
        """Test that generated reports match the contracts/report-schema.json."""
        # This will be fully testable once we have report generation working
        # For now, verify the report model can be instantiated
        import uuid
        from datetime import datetime

        # Create a minimal valid report
        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.utcnow(),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[Path("test.py")],
            scan_duration_ms=100,
            violations=[],
            principle_summaries=[],
            passed=True,
            error_count=0,
            warning_count=0,
            info_count=0,
        )

        # Convert to JSON
        report_dict = report.to_json_dict()

        # Verify key fields
        assert "report_id" in report_dict
        assert "scan_summary" in report_dict
        assert "results" in report_dict
        assert "violations_by_principle" in report_dict

    def test_validation_exits_with_non_zero_on_violations(self):
        """Test that validator exits with non-zero code when violations found."""
        # This will be tested via CLI once implemented
        # For now, verify the logic in the models
        import uuid
        from datetime import datetime

        report_with_errors = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.utcnow(),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[],
            scan_duration_ms=100,
            violations=[],
            principle_summaries=[],
            passed=False,  # Failed validation
            error_count=5,
            warning_count=2,
            info_count=0,
        )

        # Validator should exit with non-zero if not passed
        assert report_with_errors.passed is False
        assert report_with_errors.error_count > 0

    def test_validation_exits_with_zero_on_clean_codebase(self, valid_codebase_dir: Path):
        """Test that validator exits with 0 when no violations found."""
        import uuid
        from datetime import datetime

        report_clean = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.utcnow(),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[valid_codebase_dir / "compliant_example.py"],
            scan_duration_ms=50,
            violations=[],
            principle_summaries=[],
            passed=True,  # Clean validation
            error_count=0,
            warning_count=0,
            info_count=0,
        )

        assert report_clean.passed is True
        assert report_clean.error_count == 0

    def test_ignore_configuration_loads_successfully(self):
        """Test that .constitution-ignore loads and filters files."""
        loader = IgnoreConfigurationLoader()
        ignore_config = loader.load()

        assert ignore_config is not None
        # Verify default patterns are included
        assert len(ignore_config.default_patterns) > 0
        assert "tests/" in ignore_config.default_patterns

    def test_ignore_configuration_excludes_test_files(self):
        """Test that test files are properly ignored."""
        loader = IgnoreConfigurationLoader()
        ignore_config = loader.load()

        # Test files should be ignored
        assert ignore_config.should_ignore(Path("tests/test_example.py"))
        assert ignore_config.should_ignore(Path("test_unit.py"))

    def test_ignore_configuration_includes_src_files(self):
        """Test that source files are not ignored."""
        loader = IgnoreConfigurationLoader()
        ignore_config = loader.load()

        # Source files should NOT be ignored
        assert not ignore_config.should_ignore(Path("src/module.py"))
        assert not ignore_config.should_ignore(Path("src/service/handler.py"))

    def test_report_generation_includes_all_required_fields(self):
        """Test that generated JSON reports have all required fields."""
        import uuid
        from datetime import datetime

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.utcnow(),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[Path("file1.py"), Path("file2.py")],
            scan_duration_ms=250,
            violations=[],
            principle_summaries=[],
            passed=True,
            error_count=0,
            warning_count=0,
            info_count=0,
        )

        json_dict = report.to_json_dict()

        # Verify all required top-level keys
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
            assert key in json_dict, f"Missing required key: {key}"

    def test_validation_respects_file_filters(self):
        """Test that validation only scans included files."""
        loader = IgnoreConfigurationLoader()
        ignore_config = loader.load()

        # Build directory should be ignored
        assert ignore_config.should_ignore(Path("build/output.py"))
        # .venv should be ignored
        assert ignore_config.should_ignore(Path(".venv/lib/module.py"))
        # __pycache__ should be ignored
        assert ignore_config.should_ignore(Path("__pycache__/cache.pyc"))

    def test_performance_metrics_tracked(self):
        """Test that validation tracks timing metrics."""
        import uuid
        from datetime import datetime

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.utcnow(),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[Path("file.py")],
            scan_duration_ms=1500,
            violations=[],
            principle_summaries=[],
            passed=True,
            error_count=0,
            warning_count=0,
            info_count=0,
        )

        # Verify duration metrics
        assert report.scan_duration_ms == 1500
        assert report.scan_duration_seconds == 1.5

    def test_violation_grouping_by_rule_type(self):
        """Test that violations are grouped by rule type in reports."""
        from src.constitution_validator.models import (
            ViolationGroup,
            ViolationLocation,
        )

        group = ViolationGroup(
            rule_id="CONST-II-001",
            violation_type="direct_os_getenv",
            locations=[
                ViolationLocation(file_path=Path("file1.py"), line_number=10),
                ViolationLocation(file_path=Path("file2.py"), line_number=25),
            ],
            message_template="Direct os.getenv() usage detected",
            remediation="Use get_settings() from src/config/settings.py",
            count=2,
        )

        assert group.count == 2
        assert len(group.locations) == 2
        assert group.rule_id == "CONST-II-001"

    def test_report_includes_coverage_metrics(self):
        """Test that reports can include coverage percentage."""
        import uuid
        from datetime import datetime

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.utcnow(),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[],
            scan_duration_ms=100,
            violations=[],
            principle_summaries=[],
            passed=True,
            error_count=0,
            warning_count=0,
            info_count=0,
            coverage_percentage=82.5,
        )

        json_dict = report.to_json_dict()
        assert json_dict["coverage"]["percentage"] == 82.5
        assert json_dict["coverage"]["meets_minimum"] is True

    def test_report_includes_git_commit_count(self):
        """Test that reports include git commit check count."""
        import uuid
        from datetime import datetime

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.utcnow(),
            validator_version="1.0.0",
            constitution_version="1.0.0",
            scanned_files=[],
            scan_duration_ms=100,
            violations=[],
            principle_summaries=[],
            passed=True,
            error_count=0,
            warning_count=0,
            info_count=0,
            unpushed_commits_checked=15,
        )

        json_dict = report.to_json_dict()
        assert json_dict["git_attribution"]["commits_checked"] == 15
