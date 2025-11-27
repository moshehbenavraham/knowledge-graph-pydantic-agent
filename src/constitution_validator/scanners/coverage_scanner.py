"""
Test coverage scanner.

Integrates with pytest-cov to measure test coverage.
"""

import re
import subprocess  # nosec B404 - subprocess needed for pytest coverage execution
from pathlib import Path

import structlog

logger = structlog.get_logger()


class CoverageScanner:
    """Scanner for measuring test coverage using pytest-cov."""

    def __init__(self) -> None:
        """Initialize coverage scanner."""
        logger.debug("Initializing CoverageScanner")
        self.coverage_pattern = re.compile(r"TOTAL\s+\d+\s+\d+\s+(\d+(?:\.\d+)?)%")

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
        logger.info("Getting coverage", project_root=str(project_root))
        try:
            # Run pytest with coverage
            logger.debug("Running pytest with coverage")
            result = (
                subprocess.run(  # nosec B603, B607 - pytest is a trusted tool with fixed arguments
                    [
                        "pytest",
                        "--cov=src",
                        "--cov-report=term-missing",
                        "--quiet",
                        "--no-header",
                        "--continue-on-collection-errors",  # Don't stop on collection errors
                    ],
                    check=False,
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                )
            )

            # Parse coverage from output
            logger.debug("Parsing coverage from pytest output")
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
            logger.error("Could not parse coverage from pytest output")
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
        logger.debug("Parsing coverage output", output_length=len(output))
        # Look for TOTAL line with coverage percentage
        # Format: TOTAL    1234    567    78%
        match = self.coverage_pattern.search(output)

        if match:
            coverage_str = match.group(1)
            coverage = float(coverage_str)
            logger.debug("Coverage parsed from TOTAL line", coverage=coverage)
            return coverage

        # Also try to find percentage in other formats
        # Look for lines like "78% coverage" or "78.5% coverage"
        alt_pattern = re.compile(r"(\d+(?:\.\d+)?)%\s+coverage", re.IGNORECASE)
        alt_match = alt_pattern.search(output)

        if alt_match:
            coverage = float(alt_match.group(1))
            logger.debug("Coverage parsed from alternate format", coverage=coverage)
            return coverage

        logger.debug("No coverage found in output")
        return None

    def check_pytest_cov_installed(self) -> bool:
        """
        Check if pytest-cov is installed and available.

        Returns:
            True if pytest-cov is available
        """
        logger.debug("Checking if pytest-cov is installed")
        try:
            result = subprocess.run(  # nosec B603, B607 - pytest version check with fixed arguments
                ["pytest", "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            is_installed = "pytest" in result.stdout.lower()
            logger.debug("pytest-cov check complete", is_installed=is_installed)
            return is_installed

        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.debug("pytest-cov check failed", error=str(e))
            return False
