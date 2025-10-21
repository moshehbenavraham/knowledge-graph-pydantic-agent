"""
Principle IV validation rule: Test-Driven Quality Assurance.

Validates that test coverage meets the 75% minimum threshold.
"""

from pathlib import Path
from typing import List

from src.constitution_validator.models import (
    ViolationRecord,
    ViolationLocation,
    ConfidenceLevel,
)
from src.constitution_validator.rules.base import ValidationRule
from src.constitution_validator.scanners.coverage_scanner import CoverageScanner


class TestCoverageRule(ValidationRule):
    """Validates adherence to Test-Driven Quality Assurance principle."""

    def __init__(self):
        """Initialize the Test Coverage validation rule."""
        super().__init__(
            rule_id="CONST-IV-001",
            principle_id="IV",
            name="Validate test coverage >= 75%",
            description="Ensures test coverage meets minimum 75% threshold",
            violation_message_template="Test coverage is {coverage}%, below the required 75% minimum",
            remediation_guidance=(
                "Increase test coverage to at least 75%. "
                "Run 'pytest --cov=src --cov-report=term-missing' to identify untested code. "
                "Focus on critical business logic and edge cases first."
            ),
            confidence_level=ConfidenceLevel.HIGH,
            severity="error",
        )
        self.excluded_paths = [
            "tests/",
            "test_*.py",
            "*_test.py",
        ]
        self.coverage_scanner = CoverageScanner()

    def execute_coverage_check(self, project_root: Path) -> List[ViolationRecord]:
        """
        Execute coverage check for the entire project.

        Args:
            project_root: Root directory of the project

        Returns:
            List of violation records (empty if coverage meets threshold)
        """
        violations = []

        try:
            # Get coverage percentage from scanner
            coverage_percentage = self.coverage_scanner.get_coverage(project_root)

            # Check if below threshold
            if coverage_percentage < 75.0:
                violation = ViolationRecord(
                    rule_id=self.rule_id,
                    principle_id=self.principle_id,
                    location=ViolationLocation(
                        file_path=project_root / "pytest.ini",  # Symbolic location
                        line_number=1,
                    ),
                    message=self.violation_message_template.format(
                        coverage=f"{coverage_percentage:.1f}"
                    ),
                    remediation=self.remediation_guidance,
                    confidence=self.confidence_level,
                    severity=self.severity,
                    detected_code=f"Coverage: {coverage_percentage:.1f}%",
                    suggested_fix="Add more unit tests to reach 75% coverage threshold",
                    metadata={"coverage_percentage": coverage_percentage},
                )

                violations.append(violation)

        except Exception as e:
            # If coverage measurement fails, report it as a violation
            violation = ViolationRecord(
                rule_id=self.rule_id,
                principle_id=self.principle_id,
                location=ViolationLocation(
                    file_path=project_root / "pyproject.toml",
                    line_number=1,
                ),
                message=f"Failed to measure test coverage: {str(e)}",
                remediation=(
                    "Ensure pytest-cov is installed and configured. "
                    "Run 'pip install pytest-cov' and add coverage configuration to pyproject.toml."
                ),
                confidence=ConfidenceLevel.HIGH,
                severity="error",
                detected_code=str(e),
            )

            violations.append(violation)

        return violations
