"""
Test coverage scanner.

Integrates with pytest-cov to measure test coverage.
"""

import re
import subprocess
from pathlib import Path

import structlog

logger = structlog.get_logger()


class CoverageScanner:
    """Scanner for measuring test coverage using pytest-cov."""

    def __init__(self):
        """Initialize coverage scanner."""
        self.coverage_pattern = re.compile(r"TOTAL\s+\d+\s+\d+\s+(\d+)%")

    def get_coverage(self, project_root: Path) -> float:
        """
        Get test coverage percentage for the project.

        Args:
            project_root: Root directory of the project

        Returns:
            Coverage percentage (0-100)

        Raises:
            Exception: If pytest-cov is not available or coverage measurement fails
        """
        try:
            # Run pytest with coverage
            result = subprocess.run(
                [
                    "pytest",
                    "--cov=src",
                    "--cov-report=term-missing",
                    "--quiet",
                    "--no-header",
                ],
                check=False,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            # Parse coverage from output
            coverage = self._parse_coverage_output(result.stdout)

            if coverage is not None:
                logger.info("coverage_measured", coverage=coverage)
                return coverage
            # Try parsing from stderr
            coverage = self._parse_coverage_output(result.stderr)
            if coverage is not None:
                logger.info("coverage_measured_from_stderr", coverage=coverage)
                return coverage

            # If we couldn't parse coverage, raise error
            raise Exception("Could not parse coverage from pytest output")

        except FileNotFoundError:
            raise Exception("pytest not found - ensure pytest-cov is installed")

        except subprocess.TimeoutExpired:
            raise Exception("Coverage measurement timed out after 5 minutes")

        except Exception as e:
            logger.error("coverage_measurement_failed", error=str(e))
            raise

    def _parse_coverage_output(self, output: str) -> float | None:
        """
        Parse coverage percentage from pytest-cov output.

        Args:
            output: pytest coverage output text

        Returns:
            Coverage percentage, or None if not found
        """
        # Look for TOTAL line with coverage percentage
        # Format: TOTAL    1234    567    78%
        match = self.coverage_pattern.search(output)

        if match:
            coverage_str = match.group(1)
            return float(coverage_str)

        # Also try to find percentage in other formats
        # Look for lines like "78% coverage"
        alt_pattern = re.compile(r"(\d+)%\s+coverage", re.IGNORECASE)
        alt_match = alt_pattern.search(output)

        if alt_match:
            return float(alt_match.group(1))

        return None

    def check_pytest_cov_installed(self) -> bool:
        """
        Check if pytest-cov is installed and available.

        Returns:
            True if pytest-cov is available
        """
        try:
            result = subprocess.run(
                ["pytest", "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return "pytest" in result.stdout.lower()

        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
