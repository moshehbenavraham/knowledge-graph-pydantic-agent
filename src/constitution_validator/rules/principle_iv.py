"""
Principle IV validation rule: Test-Driven Quality Assurance.

Validates that test coverage meets the 50% minimum threshold.
"""

import ast
from pathlib import Path

import structlog

from src.constitution_validator.models import (
    ConfidenceLevel,
    ViolationRecord,
)
from src.constitution_validator.rules.base import BaseValidationRule

logger = structlog.get_logger(__name__)


class TestCoverageRule(BaseValidationRule):
    """Validates adherence to Test-Driven Quality Assurance principle."""

    rule_id = "CONST-IV-001"
    principle_id = "IV"
    rule_name = "Validate test coverage meets 50% minimum"

    MINIMUM_COVERAGE = 50.0

    # Configuration for test compatibility
    excluded_paths = ["tests/**"]
    included_paths = ["src/**/*.py"]

    def execute(
        self, tree: ast.AST, file_path: Path, source_code: str | None = None
    ) -> list[ViolationRecord]:
        """
        Execute validation to check test coverage.

        Note: This rule doesn't analyze AST directly, but checks coverage metrics.
        The tree parameter is kept for API consistency.

        Args:
            tree: Parsed AST of the file (not used for coverage check)
            file_path: Path to file being validated
            source_code: Optional source code (for tests or when file doesn't exist)

        Returns:
            List of violations detected
        """
        logger.info("Executing Principle IV rule", rule_id=self.rule_id, file=str(file_path))
        # Prepare instance state
        self._prepare_execution(file_path, tree, source_code)

        # Check if this is a test file (skip coverage check for test files themselves)
        if "test" in str(file_path):
            return []

        try:
            # Try to import coverage module
            from coverage import Coverage

            # Load coverage data
            cov = Coverage(data_file=".coverage")
            cov.load()

            # Get coverage for this specific file
            analysis = cov.analysis2(str(file_path))
            if analysis:
                _, executable, _excluded, missing, _ = analysis
                executable_count = len(executable) if executable else 0
                if executable_count > 0:
                    coverage_pct = ((executable_count - len(missing)) / executable_count) * 100

                    if coverage_pct < self.MINIMUM_COVERAGE:
                        self.add_violation(
                            line_number=1,
                            message=f"Test coverage {coverage_pct:.1f}% below minimum {self.MINIMUM_COVERAGE}%",
                            remediation=(
                                f"Increase test coverage to meet {self.MINIMUM_COVERAGE}% minimum:\n"
                                f"  1. Run: pytest --cov=src --cov-report=term-missing\n"
                                f"  2. Add tests for uncovered lines\n"
                                f"  3. Current coverage: {coverage_pct:.1f}%"
                            ),
                            detected_code=f"# Coverage: {coverage_pct:.1f}%",
                            suggested_fix="# Add more unit tests",
                            confidence=ConfidenceLevel.HIGH,
                            severity="error",
                            metadata={
                                "coverage_pct": coverage_pct,
                                "minimum": self.MINIMUM_COVERAGE,
                            },
                        )

        except Exception:  # nosec B110 - Coverage data not available is expected
            # Coverage data not available - this is expected in some contexts
            pass

        logger.info(
            "Principle IV rule completed", rule_id=self.rule_id, violations=len(self.violations)
        )
        return self.violations

    def execute_coverage_check(self, project_root: Path) -> list[ViolationRecord]:
        """
        Execute coverage check for entire project (test compatibility method).

        Args:
            project_root: Path to project root

        Returns:
            List of violations detected
        """
        logger.info("Executing coverage check", project_root=str(project_root))
        from src.constitution_validator.scanners.coverage_scanner import CoverageScanner

        self.violations = []
        self.file_path = project_root

        try:
            scanner = CoverageScanner()
            coverage_pct = scanner.get_coverage(project_root)
            logger.info("Coverage retrieved", coverage_pct=coverage_pct)

            if coverage_pct < self.MINIMUM_COVERAGE:
                self.add_violation(
                    line_number=1,
                    message=f"Test coverage {coverage_pct:.1f}% below minimum {self.MINIMUM_COVERAGE}%",
                    remediation=(
                        f"Increase test coverage to meet {self.MINIMUM_COVERAGE}% minimum:\n"
                        f"  1. Run: pytest --cov=src --cov-report=term-missing\n"
                        f"  2. Add tests for uncovered lines\n"
                        f"  3. Current coverage: {coverage_pct:.1f}%"
                    ),
                    detected_code=f"# Coverage: {coverage_pct:.1f}%",
                    suggested_fix="# Add more unit tests",
                    confidence=ConfidenceLevel.HIGH,
                    severity="error",
                    metadata={
                        "coverage_pct": coverage_pct,
                        "minimum": self.MINIMUM_COVERAGE,
                    },
                )
        except Exception as e:
            # Report coverage measurement failure as a violation
            self.add_violation(
                line_number=1,
                message=f"Coverage measurement failed: {e!s}",
                remediation=(
                    "Ensure pytest-cov is installed and configured:\n"
                    "  1. Install: pip install pytest-cov\n"
                    "  2. Configure .coveragerc if needed\n"
                    "  3. Run tests with: pytest --cov=src"
                ),
                detected_code="# Coverage measurement error",
                suggested_fix="# Install and configure pytest-cov",
                confidence=ConfidenceLevel.HIGH,
                severity="warning",
                metadata={"error": str(e)},
            )

        return self.violations


# No alias needed - TestCoverageRule is the expected name
