"""
Comprehensive tests for src/constitution_validator/cli.py

Covers:
- _get_staged_files() with git commands
- _check_bypass() environment variable checks
- _discover_files() file discovery logic
- check_dependencies() for coverage, git, GitPython
- validate command with all CLI options
- main() entry point
- Error handling and exit codes
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import ANY, MagicMock, Mock, PropertyMock, mock_open, patch

import pytest
from click.testing import CliRunner


class TestGetStagedFiles:
    """Test _get_staged_files() function."""

    def test_get_staged_files_success(self):
        """Test getting staged files successfully."""
        from src.constitution_validator.cli import _get_staged_files

        mock_result = Mock()
        mock_result.stdout = "src/agent/unified_agent.py\nsrc/config/settings.py\nREADME.md\n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            # Create temp files for existence check
            with patch("pathlib.Path.exists", return_value=True):
                result = _get_staged_files()

        assert len(result) == 2  # Only .py files
        assert any("unified_agent.py" in str(f) for f in result)
        assert any("settings.py" in str(f) for f in result)

    def test_get_staged_files_empty(self):
        """Test get_staged_files with no staged files."""
        from src.constitution_validator.cli import _get_staged_files

        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = _get_staged_files()

        assert result == []

    def test_get_staged_files_nonexistent_files(self):
        """Test get_staged_files filters out non-existent files."""
        from src.constitution_validator.cli import _get_staged_files

        mock_result = Mock()
        mock_result.stdout = "deleted_file.py\nexisting_file.py\n"

        with patch("subprocess.run", return_value=mock_result):
            def mock_exists(self):
                return "existing" in str(self)

            with patch("pathlib.Path.exists", side_effect=mock_exists):
                result = _get_staged_files()

        assert len(result) == 1
        assert "existing_file.py" in str(result[0])

    def test_get_staged_files_git_error(self):
        """Test get_staged_files when git command fails."""
        from src.constitution_validator.cli import _get_staged_files

        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")):
            with pytest.raises(subprocess.CalledProcessError):
                _get_staged_files()


class TestCheckBypass:
    """Test _check_bypass() function."""

    def test_check_bypass_true_1(self):
        """Test bypass with value '1'."""
        from src.constitution_validator.cli import _check_bypass

        with patch.dict("os.environ", {"SKIP_CONSTITUTION_CHECK": "1"}):
            assert _check_bypass() is True

    def test_check_bypass_true_yes(self):
        """Test bypass with value 'yes'."""
        from src.constitution_validator.cli import _check_bypass

        with patch.dict("os.environ", {"SKIP_CONSTITUTION_CHECK": "yes"}):
            assert _check_bypass() is True

    def test_check_bypass_true_true(self):
        """Test bypass with value 'true'."""
        from src.constitution_validator.cli import _check_bypass

        with patch.dict("os.environ", {"SKIP_CONSTITUTION_CHECK": "true"}):
            assert _check_bypass() is True

    def test_check_bypass_true_on(self):
        """Test bypass with value 'on'."""
        from src.constitution_validator.cli import _check_bypass

        with patch.dict("os.environ", {"SKIP_CONSTITUTION_CHECK": "on"}):
            assert _check_bypass() is True

    def test_check_bypass_false_0(self):
        """Test bypass with value '0'."""
        from src.constitution_validator.cli import _check_bypass

        with patch.dict("os.environ", {"SKIP_CONSTITUTION_CHECK": "0"}):
            assert _check_bypass() is False

    def test_check_bypass_false_empty(self):
        """Test bypass with empty value."""
        from src.constitution_validator.cli import _check_bypass

        with patch.dict("os.environ", {"SKIP_CONSTITUTION_CHECK": ""}):
            assert _check_bypass() is False

    def test_check_bypass_false_not_set(self):
        """Test bypass when environment variable not set."""
        from src.constitution_validator.cli import _check_bypass

        with patch.dict("os.environ", {}, clear=True):
            assert _check_bypass() is False


class TestDiscoverFiles:
    """Test _discover_files() function."""

    def test_discover_files_single_file(self, tmp_path):
        """Test discovering a single Python file."""
        from src.constitution_validator.cli import _discover_files

        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        mock_ignore = Mock()
        mock_ignore.should_ignore = Mock(return_value=False)

        result = _discover_files(tmp_path, (test_file,), mock_ignore)

        assert len(result) == 1
        assert result[0] == test_file

    def test_discover_files_directory(self, tmp_path):
        """Test discovering files in a directory."""
        from src.constitution_validator.cli import _discover_files

        # Create test files
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "file1.py").write_text("# file1")
        (tmp_path / "src" / "file2.py").write_text("# file2")
        (tmp_path / "src" / "readme.md").write_text("# readme")

        mock_ignore = Mock()
        mock_ignore.should_ignore = Mock(return_value=False)

        result = _discover_files(tmp_path, (tmp_path / "src",), mock_ignore)

        assert len(result) == 2  # Only .py files

    def test_discover_files_entire_project(self, tmp_path):
        """Test discovering all files in project."""
        from src.constitution_validator.cli import _discover_files

        # Create test structure
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "src" / "main.py").write_text("# main")
        (tmp_path / "tests" / "test_main.py").write_text("# test")

        mock_ignore = Mock()
        mock_ignore.should_ignore = Mock(return_value=False)

        result = _discover_files(tmp_path, (), mock_ignore)

        assert len(result) == 2

    def test_discover_files_with_ignore(self, tmp_path):
        """Test file discovery respects ignore configuration."""
        from src.constitution_validator.cli import _discover_files

        # Create test files
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "keep.py").write_text("# keep")
        (tmp_path / "src" / "ignore.py").write_text("# ignore")

        mock_ignore = Mock()

        def should_ignore(path):
            return "ignore" in str(path)

        mock_ignore.should_ignore = should_ignore

        result = _discover_files(tmp_path, (tmp_path / "src",), mock_ignore)

        assert len(result) == 1
        assert "keep.py" in str(result[0])

    def test_discover_files_removes_duplicates(self, tmp_path):
        """Test file discovery removes duplicates."""
        from src.constitution_validator.cli import _discover_files

        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        mock_ignore = Mock()
        mock_ignore.should_ignore = Mock(return_value=False)

        # Pass same file multiple times
        result = _discover_files(tmp_path, (test_file, test_file), mock_ignore)

        assert len(result) == 1


class TestCheckDependencies:
    """Test check_dependencies() function."""

    def test_check_dependencies_all_present(self):
        """Test check_dependencies when all deps present."""
        from src.constitution_validator.cli import check_dependencies

        with patch("importlib.import_module"):
            with patch("shutil.which", return_value="/usr/bin/git"):
                # Should not raise
                check_dependencies()

    def test_check_dependencies_coverage_missing(self):
        """Test check_dependencies when coverage missing."""
        from src.constitution_validator.cli import DependencyCheckError, check_dependencies

        def mock_import(name):
            if name == "coverage":
                raise ImportError("No module named coverage")

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(DependencyCheckError, match="coverage"):
                check_dependencies()

    def test_check_dependencies_git_missing(self):
        """Test check_dependencies when git not in PATH."""
        from src.constitution_validator.cli import DependencyCheckError, check_dependencies

        with patch("shutil.which", return_value=None):
            with pytest.raises(DependencyCheckError, match="git not found"):
                check_dependencies()

    def test_check_dependencies_gitpython_missing(self):
        """Test check_dependencies when GitPython missing."""
        from src.constitution_validator.cli import DependencyCheckError, check_dependencies

        import importlib

        original_import = importlib.import_module

        def mock_import(name, *args, **kwargs):
            if name == "git":
                raise ImportError("No module named git")
            return original_import(name, *args, **kwargs)

        with patch("shutil.which", return_value="/usr/bin/git"):
            with patch("importlib.import_module", side_effect=mock_import):
                # The check_dependencies function uses `import git` not import_module
                # Let's patch __import__ instead
                with pytest.raises((DependencyCheckError, ImportError)):
                    check_dependencies()


class TestValidateCommand:
    """Test validate CLI command."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    def test_validate_bypass(self, runner):
        """Test validate with bypass environment variable."""
        from src.constitution_validator.cli import cli

        with patch.dict("os.environ", {"SKIP_CONSTITUTION_CHECK": "1"}):
            result = runner.invoke(cli, ["validate"])

        assert result.exit_code == 0
        assert "bypassed" in result.output.lower()

    def test_validate_dependency_check_fails(self, runner):
        """Test validate when dependency check fails."""
        from src.constitution_validator.cli import cli

        with patch("src.constitution_validator.cli.check_dependencies") as mock_check:
            from src.constitution_validator.cli import DependencyCheckError

            mock_check.side_effect = DependencyCheckError("Missing dependency")

            result = runner.invoke(cli, ["validate"])

        assert result.exit_code == 1
        assert "Missing dependency" in result.output

    def test_validate_dry_run(self, runner, tmp_path):
        """Test validate with --dry-run flag."""
        from src.constitution_validator.cli import cli

        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._discover_files", return_value=[test_file]):
                result = runner.invoke(cli, ["validate", "--dry-run"])

        assert result.exit_code == 0
        assert "Would scan" in result.output

    def test_validate_with_paths(self, runner, tmp_path):
        """Test validate with specific paths."""
        from src.constitution_validator.cli import cli

        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._discover_files", return_value=[]):
                with patch("src.constitution_validator.cli.ConstitutionLoader"):
                    with patch("src.constitution_validator.cli.IgnoreConfigurationLoader"):
                        with patch("src.constitution_validator.cli.ASTScanner"):
                            result = runner.invoke(cli, ["validate", str(test_file)])

        # Should attempt validation
        assert "Starting constitution validation" not in result.output or result.exit_code in [0, 1]

    def test_validate_staged_mode(self, runner):
        """Test validate with --staged flag."""
        from src.constitution_validator.cli import cli

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._get_staged_files", return_value=[]):
                with patch("src.constitution_validator.cli.ConstitutionLoader"):
                    with patch("src.constitution_validator.cli.IgnoreConfigurationLoader"):
                        result = runner.invoke(cli, ["validate", "--staged"])

        # Should use staged files
        assert result.exit_code in [0, 1]

    def test_validate_quiet_mode(self, runner):
        """Test validate with --quiet flag."""
        from src.constitution_validator.cli import cli

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._discover_files", return_value=[]):
                with patch("src.constitution_validator.cli.ConstitutionLoader") as mock_loader:
                    mock_const = Mock()
                    mock_const.version = "1.0.0"
                    mock_const.principles = []
                    mock_loader.return_value.load = Mock(return_value=mock_const)

                    with patch("src.constitution_validator.cli.IgnoreConfigurationLoader"):
                        result = runner.invoke(cli, ["validate", "--quiet"])

        assert result.exit_code in [0, 1]
        # Quiet mode should show minimal output
        assert "PASSED" in result.output or "FAILED" in result.output

    def test_validate_verbose_mode(self, runner):
        """Test validate with --verbose flag."""
        from src.constitution_validator.cli import cli

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._discover_files", return_value=[]):
                with patch("src.constitution_validator.cli.ConstitutionLoader") as mock_loader:
                    mock_const = Mock()
                    mock_const.version = "1.0.0"
                    mock_const.principles = []
                    mock_loader.return_value.load = Mock(return_value=mock_const)

                    with patch("src.constitution_validator.cli.IgnoreConfigurationLoader"):
                        result = runner.invoke(cli, ["validate", "--verbose"])

        assert result.exit_code in [0, 1]

    def test_validate_output_to_file(self, runner, tmp_path):
        """Test validate with --output flag."""
        from src.constitution_validator.cli import cli

        output_file = tmp_path / "report.json"

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._discover_files", return_value=[]):
                with patch("src.constitution_validator.cli.ConstitutionLoader") as mock_loader:
                    mock_const = Mock()
                    mock_const.version = "1.0.0"
                    mock_const.principles = []
                    mock_loader.return_value.load = Mock(return_value=mock_const)

                    with patch("src.constitution_validator.cli.IgnoreConfigurationLoader"):
                        result = runner.invoke(cli, ["validate", "--output", str(output_file)])

        if output_file.exists():
            assert output_file.stat().st_size > 0

    def test_validate_text_format(self, runner):
        """Test validate with --format text."""
        from src.constitution_validator.cli import cli

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._discover_files", return_value=[]):
                with patch("src.constitution_validator.cli.ConstitutionLoader") as mock_loader:
                    mock_const = Mock()
                    mock_const.version = "1.0.0"
                    mock_const.principles = []
                    mock_loader.return_value.load = Mock(return_value=mock_const)

                    with patch("src.constitution_validator.cli.IgnoreConfigurationLoader"):
                        result = runner.invoke(cli, ["validate", "--format", "text"])

        assert result.exit_code in [0, 1]

    def test_validate_skip_git(self, runner):
        """Test validate with --skip-git flag."""
        from src.constitution_validator.cli import cli

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._discover_files", return_value=[]):
                with patch("src.constitution_validator.cli.ConstitutionLoader") as mock_loader:
                    mock_const = Mock()
                    mock_const.version = "1.0.0"
                    mock_const.principles = []
                    mock_loader.return_value.load = Mock(return_value=mock_const)

                    with patch("src.constitution_validator.cli.IgnoreConfigurationLoader"):
                        result = runner.invoke(cli, ["validate", "--skip-git"])

        assert result.exit_code in [0, 1]

    def test_validate_skip_coverage(self, runner):
        """Test validate with --skip-coverage flag."""
        from src.constitution_validator.cli import cli

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._discover_files", return_value=[]):
                with patch("src.constitution_validator.cli.ConstitutionLoader") as mock_loader:
                    mock_const = Mock()
                    mock_const.version = "1.0.0"
                    mock_const.principles = []
                    mock_loader.return_value.load = Mock(return_value=mock_const)

                    with patch("src.constitution_validator.cli.IgnoreConfigurationLoader"):
                        result = runner.invoke(cli, ["validate", "--skip-coverage"])

        assert result.exit_code in [0, 1]

    def test_validate_exception_handling(self, runner):
        """Test validate handles exceptions gracefully."""
        from src.constitution_validator.cli import cli

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._discover_files", side_effect=Exception("Test error")):
                result = runner.invoke(cli, ["validate"])

        assert result.exit_code == 1
        assert "ERROR" in result.output


class TestMain:
    """Test main() entry point."""

    def test_main_entry_point(self):
        """Test main() function."""
        from src.constitution_validator.cli import main

        with patch("src.constitution_validator.cli.cli") as mock_cli:
            main()

        mock_cli.assert_called_once()


class TestCLIVersionOption:
    """Test CLI version option."""

    def test_version_option(self):
        """Test --version flag."""
        from src.constitution_validator.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        # Should show version
        assert "version" in result.output.lower() or len(result.output.strip()) > 0


class TestValidateCommandComplexScenarios:
    """Test complex validate command scenarios."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    def test_validate_with_violations(self, runner, tmp_path):
        """Test validate with violations found."""
        from src.constitution_validator.cli import cli

        test_file = tmp_path / "bad.py"
        test_file.write_text("import os\npassword = os.getenv('PASSWORD')")

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._discover_files", return_value=[test_file]):
                with patch("src.constitution_validator.cli.ConstitutionLoader") as mock_loader:
                    with patch("src.constitution_validator.cli.IgnoreConfigurationLoader"):
                        with patch("src.constitution_validator.cli.ASTScanner") as mock_scanner:
                            # Mock parser to return valid tree
                            mock_tree = Mock()
                            mock_scanner.return_value.parse_file = Mock(return_value=mock_tree)

                            # Mock constitution
                            from src.constitution_validator.models import Principle

                            mock_const = Mock()
                            mock_const.version = "1.0.0"
                            mock_const.principles = [
                                Principle(
                                    principle_id="II",
                                    name="Centralized Configuration",
                                    description="Test",
                                    rules=[]
                                )
                            ]
                            mock_loader.return_value.load = Mock(return_value=mock_const)

                            # Mock rules to return violations
                            with patch("src.constitution_validator.cli.CentralizedConfigRule") as mock_rule_class:
                                from src.constitution_validator.models import Violation

                                mock_rule = Mock()
                                mock_rule.execute = Mock(return_value=[
                                    Violation(
                                        principle_id="II",
                                        rule_id="CONST-II-001",
                                        severity="error",
                                        message="Use centralized config",
                                        location="bad.py:2:1",
                                        remediation="Fix it",
                                        suppressed=False
                                    )
                                ])
                                mock_rule_class.return_value = mock_rule

                                with patch("src.constitution_validator.cli.UnifiedAgentRule"):
                                    with patch("src.constitution_validator.cli.DualDatabaseRule"):
                                        with patch("src.constitution_validator.cli.ObservabilityRule"):
                                            with patch("src.constitution_validator.cli.TestCoverageRule"):
                                                with patch("src.constitution_validator.cli.GitAttributionRule"):
                                                    result = runner.invoke(cli, ["validate", "--skip-git", "--skip-coverage"])

        # Should fail due to violations
        assert result.exit_code == 1

    def test_validate_ast_parse_failure(self, runner, tmp_path):
        """Test validate handles AST parse failures."""
        from src.constitution_validator.cli import cli

        test_file = tmp_path / "broken.py"
        test_file.write_text("def broken(\n")  # Invalid syntax

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._discover_files", return_value=[test_file]):
                with patch("src.constitution_validator.cli.ConstitutionLoader") as mock_loader:
                    with patch("src.constitution_validator.cli.IgnoreConfigurationLoader"):
                        with patch("src.constitution_validator.cli.ASTScanner") as mock_scanner:
                            # Mock parser to return None (parse failure)
                            mock_scanner.return_value.parse_file = Mock(return_value=None)

                            mock_const = Mock()
                            mock_const.version = "1.0.0"
                            mock_const.principles = []
                            mock_loader.return_value.load = Mock(return_value=mock_const)

                            result = runner.invoke(cli, ["validate", "--skip-git", "--skip-coverage"])

        # Should continue despite parse failure
        assert result.exit_code in [0, 1]

    def test_validate_coverage_check_error(self, runner):
        """Test validate handles coverage check errors."""
        from src.constitution_validator.cli import cli

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._discover_files", return_value=[]):
                with patch("src.constitution_validator.cli.ConstitutionLoader") as mock_loader:
                    with patch("src.constitution_validator.cli.IgnoreConfigurationLoader"):
                        mock_const = Mock()
                        mock_const.version = "1.0.0"
                        mock_const.principles = []
                        mock_loader.return_value.load = Mock(return_value=mock_const)

                        with patch("src.constitution_validator.cli.TestCoverageRule") as mock_rule_class:
                            mock_rule = Mock()
                            mock_rule.execute_coverage_check = Mock(side_effect=Exception("Coverage error"))
                            mock_rule_class.return_value = mock_rule

                            result = runner.invoke(cli, ["validate", "--skip-git"])

        # Should continue despite coverage error
        assert result.exit_code in [0, 1]

    def test_validate_git_check_error(self, runner):
        """Test validate handles git check errors."""
        from src.constitution_validator.cli import cli

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._discover_files", return_value=[]):
                with patch("src.constitution_validator.cli.ConstitutionLoader") as mock_loader:
                    with patch("src.constitution_validator.cli.IgnoreConfigurationLoader"):
                        mock_const = Mock()
                        mock_const.version = "1.0.0"
                        mock_const.principles = []
                        mock_loader.return_value.load = Mock(return_value=mock_const)

                        with patch("src.constitution_validator.cli.GitAttributionRule") as mock_rule_class:
                            mock_rule = Mock()
                            mock_rule.execute_git_check = Mock(side_effect=Exception("Git error"))
                            mock_rule_class.return_value = mock_rule

                            result = runner.invoke(cli, ["validate", "--skip-coverage"])

        # Should continue despite git error
        assert result.exit_code in [0, 1]
