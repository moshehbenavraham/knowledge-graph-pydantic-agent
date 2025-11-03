"""Unit tests for CLI functionality.

Tests quiet mode, dry-run mode, and command-line argument handling per US3.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from src.constitution_validator.cli import validate


class TestQuietMode:
    """Test T044: CLI quiet mode outputs only violation counts."""

    def test_quiet_flag_outputs_only_counts(self):
        """Test that --quiet flag suppresses detailed output."""
        runner = CliRunner()

        # Mock the validation to return some violations
        with patch("src.constitution_validator.cli.run_validation") as mock_validate:
            mock_validate.return_value = {
                "passed": False,
                "total_violations": 5,
                "error_count": 3,
                "warning_count": 2,
            }

            result = runner.invoke(validate, ["--quiet"])

            # Should only show counts, not detailed violations
            assert "3 errors" in result.output or "3" in result.output
            assert "2 warnings" in result.output or "2" in result.output

            # Should not show detailed file paths or remediation
            assert "remediation" not in result.output.lower()
            assert "Fix:" not in result.output

    def test_quiet_mode_exit_code_on_violations(self):
        """Test that quiet mode returns non-zero exit code on violations."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli.run_validation") as mock_validate:
            mock_validate.return_value = {
                "passed": False,
                "total_violations": 5,
                "error_count": 3,
            }

            result = runner.invoke(validate, ["--quiet"])
            assert result.exit_code != 0  # Non-zero on violations

    def test_quiet_mode_exit_code_on_success(self):
        """Test that quiet mode returns zero exit code when no violations."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli.run_validation") as mock_validate:
            mock_validate.return_value = {
                "passed": True,
                "total_violations": 0,
                "error_count": 0,
            }

            result = runner.invoke(validate, ["--quiet"])
            assert result.exit_code == 0  # Zero on success

    def test_quiet_mode_suitable_for_scripting(self):
        """Test that quiet mode output is parseable for CI/CD scripts."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli.run_validation") as mock_validate:
            mock_validate.return_value = {
                "passed": False,
                "total_violations": 5,
                "error_count": 3,
                "warning_count": 2,
            }

            result = runner.invoke(validate, ["--quiet"])

            # Output should be simple and parseable
            lines = result.output.strip().split("\n")
            # Should have minimal lines (not verbose output)
            assert len(lines) <= 5, "Quiet mode should have minimal output"


class TestDryRunMode:
    """Test T045: CLI dry-run mode shows what would be checked without validation."""

    def test_dry_run_shows_files_to_check(self):
        """Test that --dry-run lists files that would be validated."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli.discover_files") as mock_discover:
            mock_discover.return_value = [
                Path("src/file1.py"),
                Path("src/file2.py"),
                Path("src/file3.py"),
            ]

            result = runner.invoke(validate, ["--dry-run"])

            # Should show files that would be checked
            assert "src/file1.py" in result.output
            assert "src/file2.py" in result.output
            assert "src/file3.py" in result.output

    def test_dry_run_shows_rules_to_execute(self):
        """Test that --dry-run lists rules that would be executed."""
        runner = CliRunner()

        result = runner.invoke(validate, ["--dry-run"])

        # Should show which principles/rules will be checked
        assert "Principle I" in result.output or "CONST-I" in result.output
        assert "Principle II" in result.output or "CONST-II" in result.output
        # ... (should list all 6 principles)

    def test_dry_run_minimal_execution_time(self):
        """Test that --dry-run completes quickly without full validation."""
        import time

        runner = CliRunner()

        start_time = time.time()
        _result = runner.invoke(validate, ["--dry-run", "src/"])
        end_time = time.time()

        execution_time = end_time - start_time

        # Dry-run should be fast (< 1 second for file discovery)
        assert execution_time < 1.0, f"Dry-run took {execution_time}s, should be <1s"

    def test_dry_run_exit_code_zero(self):
        """Test that --dry-run always returns zero exit code (no actual validation)."""
        runner = CliRunner()

        result = runner.invoke(validate, ["--dry-run"])

        # Dry-run should always succeed (it's just showing what would happen)
        assert result.exit_code == 0

    def test_dry_run_output_format(self):
        """Test that --dry-run output format is clear and structured."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli.discover_files") as mock_discover:
            mock_discover.return_value = [Path("src/file1.py")]

            result = runner.invoke(validate, ["--dry-run"])

            # Should have clear sections
            output_lower = result.output.lower()
            assert "would check" in output_lower or "files to validate" in output_lower
            assert "rules to execute" in output_lower or "principles to check" in output_lower


class TestPreCommitHookIntegration:
    """Test T046: Pre-commit hook integration and performance."""

    def test_hook_blocks_commit_with_violations(self):
        """Test that pre-commit hook returns non-zero code on violations."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli.run_validation") as mock_validate:
            mock_validate.return_value = {
                "passed": False,
                "total_violations": 2,
                "error_count": 2,
            }

            # Simulate pre-commit hook invocation with staged files
            result = runner.invoke(
                validate,
                ["src/file1.py", "src/file2.py"],  # Specific files from git diff --cached
            )

            # Should fail (non-zero exit code)
            assert result.exit_code != 0

    def test_hook_allows_commit_without_violations(self):
        """Test that pre-commit hook returns zero code when no violations."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli.run_validation") as mock_validate:
            mock_validate.return_value = {
                "passed": True,
                "total_violations": 0,
                "error_count": 0,
            }

            # Simulate pre-commit hook invocation
            result = runner.invoke(
                validate,
                ["src/file1.py"],
            )

            # Should succeed (zero exit code)
            assert result.exit_code == 0

    @pytest.mark.slow
    def test_incremental_validation_performance(self):
        """Test that incremental validation (pre-commit mode) completes in <5s."""
        import time

        runner = CliRunner()

        # Create mock files for realistic test
        test_files = [f"src/file{i}.py" for i in range(5)]  # 5 files

        with patch("src.constitution_validator.cli.run_validation") as mock_validate:
            mock_validate.return_value = {
                "passed": True,
                "total_violations": 0,
                "error_count": 0,
            }

            start_time = time.time()
            _result = runner.invoke(validate, test_files)
            end_time = time.time()

            execution_time = end_time - start_time

            # Pre-commit should complete in <5s per SC-007
            assert (
                execution_time < 5.0
            ), f"Incremental validation took {execution_time}s, should be <5s"

    def test_hook_shows_violation_summary_on_failure(self):
        """Test that hook failure shows helpful violation summary."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli.run_validation") as mock_validate:
            mock_validate.return_value = {
                "passed": False,
                "total_violations": 3,
                "error_count": 3,
                "violations_by_principle": [
                    {
                        "principle_id": "II",
                        "principle_name": "Centralized Configuration",
                        "violation_count": 3,
                    }
                ],
            }

            result = runner.invoke(validate, ["src/file.py"])

            # Should show summary of violations
            assert "3" in result.output  # violation count
            assert "Principle II" in result.output or "Configuration" in result.output

    def test_hook_exit_code_matches_validation_result(self):
        """Test that exit code correctly reflects validation pass/fail."""
        runner = CliRunner()

        # Test case 1: Violations found
        with patch("src.constitution_validator.cli.run_validation") as mock_validate:
            mock_validate.return_value = {"passed": False, "error_count": 5}
            result = runner.invoke(validate, [])
            assert result.exit_code != 0

        # Test case 2: No violations
        with patch("src.constitution_validator.cli.run_validation") as mock_validate:
            mock_validate.return_value = {"passed": True, "error_count": 0}
            result = runner.invoke(validate, [])
            assert result.exit_code == 0


class TestCLIArgumentParsing:
    """Test CLI argument validation and help text."""

    def test_accepts_file_paths(self):
        """Test that CLI accepts file paths as arguments."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli.run_validation") as mock_validate:
            mock_validate.return_value = {"passed": True}

            result = runner.invoke(
                validate,
                ["src/file1.py", "src/file2.py"],
            )

            # Should accept file paths without error
            assert "Invalid" not in result.output

    def test_accepts_directory_paths(self):
        """Test that CLI accepts directory paths as arguments."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli.run_validation") as mock_validate:
            mock_validate.return_value = {"passed": True}

            result = runner.invoke(
                validate,
                ["src/", "tests/"],
            )

            # Should accept directory paths
            assert result.exit_code == 0 or "Invalid" not in result.output

    def test_help_text_comprehensive(self):
        """Test that --help shows comprehensive usage information."""
        runner = CliRunner()

        result = runner.invoke(validate, ["--help"])

        # Should describe all flags
        assert "--quiet" in result.output
        assert "--verbose" in result.output
        assert "--dry-run" in result.output

        # Should have usage examples or description
        assert "constitution" in result.output.lower() or "validate" in result.output.lower()
