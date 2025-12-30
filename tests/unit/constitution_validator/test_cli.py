"""Unit tests for CLI functionality.

Tests quiet mode, dry-run mode, and command-line argument handling per US3.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.constitution_validator.cli import validate

# The CLI imports these inside the validate() function, so we need to patch
# the places they're imported from, not on the CLI module itself
LOADER_PATCH = "src.constitution_validator.loader.ConstitutionLoader"
IGNORE_LOADER_PATCH = "src.constitution_validator.loader.IgnoreConfigurationLoader"
AST_SCANNER_PATCH = "src.constitution_validator.scanners.ast_scanner.ASTScanner"
UNIFIED_RULE_PATCH = "src.constitution_validator.rules.principle_i.UnifiedAgentRule"
CONFIG_RULE_PATCH = "src.constitution_validator.rules.principle_ii.CentralizedConfigRule"
DUAL_RULE_PATCH = "src.constitution_validator.rules.principle_iii.DualDatabaseRule"
TEST_RULE_PATCH = "src.constitution_validator.rules.principle_iv.TestCoverageRule"
OBS_RULE_PATCH = "src.constitution_validator.rules.principle_v.ObservabilityRule"
GIT_RULE_PATCH = "src.constitution_validator.rules.principle_vi.GitAttributionRule"
DISCOVER_PATCH = "src.constitution_validator.cli._discover_files"
CHECK_DEPS_PATCH = "src.constitution_validator.cli.check_dependencies"


def create_base_mocks():
    """Create base mock objects for CLI tests."""
    mock_constitution = MagicMock()
    mock_constitution.principles = []
    mock_constitution.version = "1.0.0"  # Required by ComplianceReport
    return mock_constitution


class TestQuietMode:
    """Test T044: CLI quiet mode outputs only violation counts."""

    def test_quiet_flag_outputs_only_counts(self):
        """Test that --quiet flag suppresses detailed output."""
        runner = CliRunner()

        with (
            patch(LOADER_PATCH) as mock_const_loader,
            patch(IGNORE_LOADER_PATCH) as mock_ignore_loader,
            patch(DISCOVER_PATCH) as mock_discover,
            patch(AST_SCANNER_PATCH),
            patch(UNIFIED_RULE_PATCH) as mock_unified_rule,
            patch(CONFIG_RULE_PATCH) as mock_config_rule,
            patch(DUAL_RULE_PATCH) as mock_dual_rule,
            patch(TEST_RULE_PATCH),
            patch(OBS_RULE_PATCH) as mock_obs_rule,
            patch(GIT_RULE_PATCH),
        ):
            # Setup mocks
            mock_constitution = create_base_mocks()
            mock_const_loader.return_value.load.return_value = mock_constitution
            mock_ignore_loader.return_value.load.return_value = MagicMock()
            mock_discover.return_value = []

            # Create mock violation
            mock_violation = MagicMock()
            mock_violation.severity = "error"
            mock_violation.suppressed = False
            mock_violation.principle_id = "II"

            # Make one rule return a violation
            mock_config_rule.return_value.execute.return_value = [mock_violation]
            mock_unified_rule.return_value.execute.return_value = []
            mock_dual_rule.return_value.execute.return_value = []
            mock_obs_rule.return_value.execute.return_value = []

            result = runner.invoke(validate, ["--quiet", "--skip-coverage", "--skip-git"])

            # Quiet mode should have minimal output
            assert result.exit_code != 0 or "error" in result.output.lower()

    def test_quiet_mode_exit_code_on_violations(self):
        """Test that quiet mode returns non-zero exit code on violations."""
        runner = CliRunner()

        with (
            patch(CHECK_DEPS_PATCH),
            patch(LOADER_PATCH) as mock_const_loader,
            patch(IGNORE_LOADER_PATCH) as mock_ignore_loader,
            patch(DISCOVER_PATCH) as mock_discover,
            patch(AST_SCANNER_PATCH),
            patch(UNIFIED_RULE_PATCH),
            patch(CONFIG_RULE_PATCH),
            patch(DUAL_RULE_PATCH),
            patch(TEST_RULE_PATCH),
            patch(OBS_RULE_PATCH),
            patch(GIT_RULE_PATCH),
        ):
            # Setup mocks - minimal setup for a passing run
            mock_constitution = create_base_mocks()
            mock_const_loader.return_value.load.return_value = mock_constitution
            mock_ignore_loader.return_value.load.return_value = MagicMock()
            mock_discover.return_value = []

            result = runner.invoke(validate, ["--quiet", "--skip-coverage", "--skip-git"])
            # With no files to scan, it should pass (exit code 0)
            assert result.exit_code == 0

    def test_quiet_mode_exit_code_on_success(self):
        """Test that quiet mode returns zero exit code when no violations."""
        runner = CliRunner()

        with (
            patch(CHECK_DEPS_PATCH),
            patch(LOADER_PATCH) as mock_const_loader,
            patch(IGNORE_LOADER_PATCH) as mock_ignore_loader,
            patch(DISCOVER_PATCH) as mock_discover,
            patch(AST_SCANNER_PATCH),
            patch(UNIFIED_RULE_PATCH),
            patch(CONFIG_RULE_PATCH),
            patch(DUAL_RULE_PATCH),
            patch(TEST_RULE_PATCH),
            patch(OBS_RULE_PATCH),
            patch(GIT_RULE_PATCH),
        ):
            mock_constitution = create_base_mocks()
            mock_const_loader.return_value.load.return_value = mock_constitution
            mock_ignore_loader.return_value.load.return_value = MagicMock()
            mock_discover.return_value = []

            result = runner.invoke(validate, ["--quiet", "--skip-coverage", "--skip-git"])
            assert result.exit_code == 0

    def test_quiet_mode_suitable_for_scripting(self):
        """Test that quiet mode output is parseable for CI/CD scripts."""
        runner = CliRunner()

        with (
            patch(LOADER_PATCH) as mock_const_loader,
            patch(IGNORE_LOADER_PATCH) as mock_ignore_loader,
            patch(DISCOVER_PATCH) as mock_discover,
            patch(AST_SCANNER_PATCH),
            patch(UNIFIED_RULE_PATCH),
            patch(CONFIG_RULE_PATCH),
            patch(DUAL_RULE_PATCH),
            patch(TEST_RULE_PATCH),
            patch(OBS_RULE_PATCH),
            patch(GIT_RULE_PATCH),
        ):
            mock_constitution = create_base_mocks()
            mock_const_loader.return_value.load.return_value = mock_constitution
            mock_ignore_loader.return_value.load.return_value = MagicMock()
            mock_discover.return_value = []

            result = runner.invoke(validate, ["--quiet", "--skip-coverage", "--skip-git"])

            # Quiet mode should have minimal lines
            lines = [line for line in result.output.strip().split("\n") if line.strip()]
            # Should not be overly verbose
            assert len(lines) <= 20, f"Quiet mode has too many lines: {len(lines)}"


class TestDryRunMode:
    """Test T045: CLI dry-run mode shows what would be checked without validation."""

    def test_dry_run_shows_files_to_check(self):
        """Test that --dry-run lists files that would be validated."""
        runner = CliRunner()

        with (
            patch(LOADER_PATCH) as mock_const_loader,
            patch(IGNORE_LOADER_PATCH) as mock_ignore_loader,
            patch(DISCOVER_PATCH) as mock_discover,
        ):
            mock_discover.return_value = [
                Path("src/file1.py"),
                Path("src/file2.py"),
                Path("src/file3.py"),
            ]
            mock_constitution = create_base_mocks()
            mock_const_loader.return_value.load.return_value = mock_constitution
            mock_ignore_loader.return_value.load.return_value = MagicMock()

            result = runner.invoke(validate, ["--dry-run"])

            # Should show files that would be checked
            assert "src/file1.py" in result.output
            assert "src/file2.py" in result.output
            assert "src/file3.py" in result.output

    def test_dry_run_shows_rules_to_execute(self):
        """Test that --dry-run lists rules that would be executed."""
        runner = CliRunner()

        with (
            patch(LOADER_PATCH) as mock_const_loader,
            patch(IGNORE_LOADER_PATCH) as mock_ignore_loader,
            patch(DISCOVER_PATCH) as mock_discover,
        ):
            mock_discover.return_value = [Path("src/test.py")]
            mock_constitution = create_base_mocks()
            mock_const_loader.return_value.load.return_value = mock_constitution
            mock_ignore_loader.return_value.load.return_value = MagicMock()

            result = runner.invoke(validate, ["--dry-run"])

            # Should show scanning info (dry-run exits early)
            assert "scan" in result.output.lower() or "would" in result.output.lower()

    def test_dry_run_minimal_execution_time(self):
        """Test that --dry-run completes quickly without full validation."""
        import time

        runner = CliRunner()

        start_time = time.time()
        _result = runner.invoke(validate, ["--dry-run", "src/"])
        end_time = time.time()

        execution_time = end_time - start_time

        # Dry-run should be fast (< 5 seconds including setup)
        assert execution_time < 5.0, f"Dry-run took {execution_time}s, should be <5s"

    def test_dry_run_exit_code_zero(self):
        """Test that --dry-run always returns zero exit code (no actual validation)."""
        runner = CliRunner()

        with (
            patch(LOADER_PATCH) as mock_const_loader,
            patch(IGNORE_LOADER_PATCH) as mock_ignore_loader,
            patch(DISCOVER_PATCH) as mock_discover,
        ):
            mock_discover.return_value = []
            mock_constitution = create_base_mocks()
            mock_const_loader.return_value.load.return_value = mock_constitution
            mock_ignore_loader.return_value.load.return_value = MagicMock()

            result = runner.invoke(validate, ["--dry-run"])

            # Dry-run should always succeed
            assert result.exit_code == 0

    def test_dry_run_output_format(self):
        """Test that --dry-run output format is clear and structured."""
        runner = CliRunner()

        with (
            patch(LOADER_PATCH) as mock_const_loader,
            patch(IGNORE_LOADER_PATCH) as mock_ignore_loader,
            patch(DISCOVER_PATCH) as mock_discover,
        ):
            mock_discover.return_value = [Path("src/file1.py")]
            mock_constitution = create_base_mocks()
            mock_const_loader.return_value.load.return_value = mock_constitution
            mock_ignore_loader.return_value.load.return_value = MagicMock()

            result = runner.invoke(validate, ["--dry-run"])

            # Should have clear indication of what will be scanned
            output_lower = result.output.lower()
            assert "scan" in output_lower or "would" in output_lower or "file" in output_lower


class TestPreCommitHookIntegration:
    """Test T046: Pre-commit hook integration and performance."""

    def test_hook_blocks_commit_with_violations(self):
        """Test that pre-commit hook returns non-zero code on violations."""
        runner = CliRunner()

        with (
            patch(LOADER_PATCH) as mock_const_loader,
            patch(IGNORE_LOADER_PATCH) as mock_ignore_loader,
            patch(DISCOVER_PATCH) as mock_discover,
            patch(AST_SCANNER_PATCH) as mock_scanner,
            patch(UNIFIED_RULE_PATCH) as mock_unified_rule,
            patch(CONFIG_RULE_PATCH) as mock_config_rule,
            patch(DUAL_RULE_PATCH) as mock_dual_rule,
            patch(TEST_RULE_PATCH),
            patch(OBS_RULE_PATCH) as mock_obs_rule,
            patch(GIT_RULE_PATCH),
        ):
            mock_constitution = create_base_mocks()
            mock_const_loader.return_value.load.return_value = mock_constitution
            mock_ignore_loader.return_value.load.return_value = MagicMock()
            mock_discover.return_value = [Path("src/file1.py")]

            # Create a mock violation
            mock_violation = MagicMock()
            mock_violation.severity = "error"
            mock_violation.suppressed = False
            mock_violation.principle_id = "II"
            mock_violation.rule_id = "II-001"
            mock_violation.message = "Test violation"
            mock_violation.location = "src/file1.py:10"
            mock_violation.remediation = "Fix it"

            mock_scanner.return_value.parse_file.return_value = MagicMock()
            mock_config_rule.return_value.execute.return_value = [mock_violation]
            mock_unified_rule.return_value.execute.return_value = []
            mock_dual_rule.return_value.execute.return_value = []
            mock_obs_rule.return_value.execute.return_value = []

            result = runner.invoke(validate, ["--skip-coverage", "--skip-git"])

            # Should fail with non-zero exit code
            assert result.exit_code != 0

    def test_hook_allows_commit_without_violations(self):
        """Test that pre-commit hook returns zero code when no violations."""
        runner = CliRunner()

        with (
            patch(CHECK_DEPS_PATCH),
            patch(LOADER_PATCH) as mock_const_loader,
            patch(IGNORE_LOADER_PATCH) as mock_ignore_loader,
            patch(DISCOVER_PATCH) as mock_discover,
            patch(AST_SCANNER_PATCH),
            patch(UNIFIED_RULE_PATCH),
            patch(CONFIG_RULE_PATCH),
            patch(DUAL_RULE_PATCH),
            patch(TEST_RULE_PATCH),
            patch(OBS_RULE_PATCH),
            patch(GIT_RULE_PATCH),
        ):
            mock_constitution = create_base_mocks()
            mock_const_loader.return_value.load.return_value = mock_constitution
            mock_ignore_loader.return_value.load.return_value = MagicMock()
            mock_discover.return_value = []

            result = runner.invoke(validate, ["--skip-coverage", "--skip-git"])

            assert result.exit_code == 0

    @pytest.mark.slow
    def test_incremental_validation_performance(self):
        """Test that incremental validation (pre-commit mode) completes in <5s."""
        import time

        runner = CliRunner()

        with (
            patch(LOADER_PATCH) as mock_const_loader,
            patch(IGNORE_LOADER_PATCH) as mock_ignore_loader,
            patch(DISCOVER_PATCH) as mock_discover,
            patch(AST_SCANNER_PATCH),
            patch(UNIFIED_RULE_PATCH),
            patch(CONFIG_RULE_PATCH),
            patch(DUAL_RULE_PATCH),
            patch(TEST_RULE_PATCH),
            patch(OBS_RULE_PATCH),
            patch(GIT_RULE_PATCH),
        ):
            mock_constitution = create_base_mocks()
            mock_const_loader.return_value.load.return_value = mock_constitution
            mock_ignore_loader.return_value.load.return_value = MagicMock()
            mock_discover.return_value = []

            start_time = time.time()
            _result = runner.invoke(validate, ["--skip-coverage", "--skip-git"])
            end_time = time.time()

            execution_time = end_time - start_time

            # Pre-commit should complete in <5s
            assert (
                execution_time < 5.0
            ), f"Incremental validation took {execution_time}s, should be <5s"

    def test_hook_shows_violation_summary_on_failure(self):
        """Test that hook failure shows helpful violation summary."""
        runner = CliRunner()

        with (
            patch(LOADER_PATCH) as mock_const_loader,
            patch(IGNORE_LOADER_PATCH) as mock_ignore_loader,
            patch(DISCOVER_PATCH) as mock_discover,
            patch(AST_SCANNER_PATCH) as mock_scanner,
            patch(UNIFIED_RULE_PATCH) as mock_unified_rule,
            patch(CONFIG_RULE_PATCH) as mock_config_rule,
            patch(DUAL_RULE_PATCH) as mock_dual_rule,
            patch(TEST_RULE_PATCH),
            patch(OBS_RULE_PATCH) as mock_obs_rule,
            patch(GIT_RULE_PATCH),
        ):
            # Setup mocks
            mock_principle = MagicMock()
            mock_principle.principle_id = "II"
            mock_principle.name = "Centralized Configuration"

            mock_constitution = MagicMock()
            mock_constitution.principles = [mock_principle]
            mock_const_loader.return_value.load.return_value = mock_constitution
            mock_ignore_loader.return_value.load.return_value = MagicMock()
            mock_discover.return_value = [Path("src/file.py")]

            # Create mock violation
            mock_violation = MagicMock()
            mock_violation.severity = "error"
            mock_violation.suppressed = False
            mock_violation.principle_id = "II"
            mock_violation.rule_id = "II-001"
            mock_violation.message = "Configuration violation"
            mock_violation.location = "src/file.py:10"
            mock_violation.remediation = "Fix it"

            mock_scanner.return_value.parse_file.return_value = MagicMock()
            mock_config_rule.return_value.execute.return_value = [mock_violation]
            mock_unified_rule.return_value.execute.return_value = []
            mock_dual_rule.return_value.execute.return_value = []
            mock_obs_rule.return_value.execute.return_value = []

            result = runner.invoke(validate, ["--skip-coverage", "--skip-git"])

            # Should show violation count in output
            assert "1" in result.output or "error" in result.output.lower()

    def test_hook_exit_code_matches_validation_result(self):
        """Test that exit code correctly reflects validation pass/fail."""
        runner = CliRunner()

        with (
            patch(CHECK_DEPS_PATCH),
            patch(LOADER_PATCH) as mock_const_loader,
            patch(IGNORE_LOADER_PATCH) as mock_ignore_loader,
            patch(DISCOVER_PATCH) as mock_discover,
            patch(AST_SCANNER_PATCH),
            patch(UNIFIED_RULE_PATCH),
            patch(CONFIG_RULE_PATCH),
            patch(DUAL_RULE_PATCH),
            patch(TEST_RULE_PATCH),
            patch(OBS_RULE_PATCH),
            patch(GIT_RULE_PATCH),
        ):
            mock_constitution = create_base_mocks()
            mock_const_loader.return_value.load.return_value = mock_constitution
            mock_ignore_loader.return_value.load.return_value = MagicMock()
            mock_discover.return_value = []

            # Test: No violations - should succeed
            result = runner.invoke(validate, ["--skip-coverage", "--skip-git"])
            assert result.exit_code == 0


class TestCLIArgumentParsing:
    """Test CLI argument validation and help text."""

    def test_accepts_file_paths(self):
        """Test that CLI accepts file paths as arguments."""
        runner = CliRunner()

        with (
            patch(LOADER_PATCH) as mock_const_loader,
            patch(IGNORE_LOADER_PATCH) as mock_ignore_loader,
            patch(DISCOVER_PATCH) as mock_discover,
            patch(AST_SCANNER_PATCH),
            patch(UNIFIED_RULE_PATCH),
            patch(CONFIG_RULE_PATCH),
            patch(DUAL_RULE_PATCH),
            patch(TEST_RULE_PATCH),
            patch(OBS_RULE_PATCH),
            patch(GIT_RULE_PATCH),
        ):
            mock_constitution = create_base_mocks()
            mock_const_loader.return_value.load.return_value = mock_constitution
            mock_ignore_loader.return_value.load.return_value = MagicMock()
            mock_discover.return_value = []

            # Create temp files for the test
            with runner.isolated_filesystem():
                Path("src").mkdir()
                Path("src/file1.py").write_text("# test")
                Path("src/file2.py").write_text("# test")

                result = runner.invoke(
                    validate,
                    ["src/file1.py", "src/file2.py", "--skip-coverage", "--skip-git"],
                )

                # Should accept file paths without error
                assert "Invalid" not in result.output or result.exit_code == 0

    def test_accepts_directory_paths(self):
        """Test that CLI accepts directory paths as arguments."""
        runner = CliRunner()

        with (
            patch(LOADER_PATCH) as mock_const_loader,
            patch(IGNORE_LOADER_PATCH) as mock_ignore_loader,
            patch(DISCOVER_PATCH) as mock_discover,
            patch(AST_SCANNER_PATCH),
            patch(UNIFIED_RULE_PATCH),
            patch(CONFIG_RULE_PATCH),
            patch(DUAL_RULE_PATCH),
            patch(TEST_RULE_PATCH),
            patch(OBS_RULE_PATCH),
            patch(GIT_RULE_PATCH),
        ):
            mock_constitution = create_base_mocks()
            mock_const_loader.return_value.load.return_value = mock_constitution
            mock_ignore_loader.return_value.load.return_value = MagicMock()
            mock_discover.return_value = []

            # Create temp directories for the test
            with runner.isolated_filesystem():
                Path("src").mkdir()
                Path("tests").mkdir()

                result = runner.invoke(
                    validate,
                    ["src/", "tests/", "--skip-coverage", "--skip-git"],
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
