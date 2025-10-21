"""
Unit tests for Principle IV validation rule (Test-Driven Quality Assurance).

Tests pytest-cov integration and coverage percentage validation.
"""

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.constitution_validator.models import (
    RuleCategory,
    ValidationRule,
    ViolationRecord,
    ConfidenceLevel,
)
from src.constitution_validator.rules.principle_iv import TestCoverageRule


class TestPrincipleIVRule:
    """Test suite for Principle IV: Test-Driven Quality Assurance validation."""

    @pytest.fixture
    def rule(self) -> TestCoverageRule:
        """Create a TestCoverageRule instance for testing."""
        return TestCoverageRule()

    @patch('src.constitution_validator.scanners.coverage_scanner.CoverageScanner.get_coverage')
    def test_detects_coverage_below_75_percent(self, mock_get_coverage, rule: TestCoverageRule):
        """Test detection when coverage is below 75%."""
        mock_get_coverage.return_value = 65.5

        violations = rule.execute_coverage_check(Path("/project/root"))

        assert len(violations) == 1
        assert violations[0].rule_id == "CONST-IV-001"
        assert violations[0].principle_id == "IV"
        assert "65.5" in violations[0].message or "65" in violations[0].message
        assert "75" in violations[0].message

    @patch('src.constitution_validator.scanners.coverage_scanner.CoverageScanner.get_coverage')
    def test_passes_when_coverage_meets_75_percent(self, mock_get_coverage, rule: TestCoverageRule):
        """Test no violation when coverage is exactly 75%."""
        mock_get_coverage.return_value = 75.0

        violations = rule.execute_coverage_check(Path("/project/root"))

        assert len(violations) == 0

    @patch('src.constitution_validator.scanners.coverage_scanner.CoverageScanner.get_coverage')
    def test_passes_when_coverage_exceeds_75_percent(self, mock_get_coverage, rule: TestCoverageRule):
        """Test no violation when coverage exceeds 75%."""
        mock_get_coverage.return_value = 92.3

        violations = rule.execute_coverage_check(Path("/project/root"))

        assert len(violations) == 0

    @patch('src.constitution_validator.scanners.coverage_scanner.CoverageScanner.get_coverage')
    def test_detects_very_low_coverage(self, mock_get_coverage, rule: TestCoverageRule):
        """Test detection of very low coverage."""
        mock_get_coverage.return_value = 15.8

        violations = rule.execute_coverage_check(Path("/project/root"))

        assert len(violations) == 1
        assert violations[0].severity == "error"

    @patch('src.constitution_validator.scanners.coverage_scanner.CoverageScanner.get_coverage')
    def test_handles_coverage_measurement_error(self, mock_get_coverage, rule: TestCoverageRule):
        """Test handling when pytest-cov fails."""
        mock_get_coverage.side_effect = Exception("pytest-cov not configured")

        violations = rule.execute_coverage_check(Path("/project/root"))

        # Should report the error as a violation or warning
        assert len(violations) >= 1
        assert any("error" in v.message.lower() or "failed" in v.message.lower() for v in violations)

    def test_exempts_test_files_themselves(self, rule: TestCoverageRule):
        """Test that test files are not counted in coverage violations."""
        # Test files should be in excluded_paths
        assert any("tests/" in path or "test_" in path for path in rule.excluded_paths)

    @patch('src.constitution_validator.scanners.coverage_scanner.CoverageScanner.get_coverage')
    def test_remediation_mentions_pytest_cov(self, mock_get_coverage, rule: TestCoverageRule):
        """Test that remediation mentions pytest-cov and how to improve coverage."""
        mock_get_coverage.return_value = 50.0

        violations = rule.execute_coverage_check(Path("/project"))

        assert len(violations) == 1
        remediation = violations[0].remediation.lower()
        assert "test" in remediation
        assert "coverage" in remediation
        assert "75" in remediation

    @patch('src.constitution_validator.scanners.coverage_scanner.CoverageScanner.get_coverage')
    def test_confidence_level_is_high(self, mock_get_coverage, rule: TestCoverageRule):
        """Test that coverage measurement has HIGH confidence."""
        mock_get_coverage.return_value = 60.0

        violations = rule.execute_coverage_check(Path("/project"))

        assert violations[0].confidence == ConfidenceLevel.HIGH

    @patch('src.constitution_validator.scanners.coverage_scanner.CoverageScanner.get_coverage')
    def test_violation_includes_current_coverage(self, mock_get_coverage, rule: TestCoverageRule):
        """Test that violation message includes the actual coverage percentage."""
        mock_get_coverage.return_value = 68.2

        violations = rule.execute_coverage_check(Path("/project"))

        assert len(violations) == 1
        assert "68" in violations[0].message

    @patch('src.constitution_validator.scanners.coverage_scanner.CoverageScanner.get_coverage')
    def test_severity_is_error(self, mock_get_coverage, rule: TestCoverageRule):
        """Test that low coverage is an error."""
        mock_get_coverage.return_value = 50.0

        violations = rule.execute_coverage_check(Path("/project"))

        assert violations[0].severity == "error"

    @patch('src.constitution_validator.scanners.coverage_scanner.CoverageScanner.get_coverage')
    def test_handles_zero_coverage(self, mock_get_coverage, rule: TestCoverageRule):
        """Test handling of 0% coverage."""
        mock_get_coverage.return_value = 0.0

        violations = rule.execute_coverage_check(Path("/project"))

        assert len(violations) == 1
        assert "0" in violations[0].message

    @patch('src.constitution_validator.scanners.coverage_scanner.CoverageScanner.get_coverage')
    def test_handles_coverage_near_threshold(self, mock_get_coverage, rule: TestCoverageRule):
        """Test coverage just below threshold."""
        mock_get_coverage.return_value = 74.9

        violations = rule.execute_coverage_check(Path("/project"))

        assert len(violations) == 1
