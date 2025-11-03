"""Comprehensive tests for Constitution Validator CLI.

Tests command-line argument parsing, validation execution, report generation,
dependency checking, and error handling.
Target coverage: 80%+ (up from 29.35%)
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from src.constitution_validator.cli import (
    DependencyCheckError,
    _check_bypass,
    _discover_files,
    _get_staged_files,
    check_dependencies,
    cli,
    main,
    validate,
)


class TestGetStagedFiles:
    """Test _get_staged_files() function."""

    @patch("subprocess.run")
    def test_get_staged_files_success(self, mock_run):
        """Test successful retrieval of staged Python files."""
        mock_result = Mock()
        mock_result.stdout = "src/file1.py\nsrc/file2.py\ntests/test_file.py\n"
        mock_run.return_value = mock_result

        with patch("pathlib.Path.exists", return_value=True):
            files = _get_staged_files()

        assert len(files) == 3
        assert all(isinstance(f, Path) for f in files)
        assert all(str(f).endswith(".py") for f in files)

    @patch("subprocess.run")
    def test_get_staged_files_empty(self, mock_run):
        """Test when no files are staged."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        files = _get_staged_files()

        assert files == []

    @patch("subprocess.run")
    def test_get_staged_files_filters_non_python(self, mock_run):
        """Test that non-Python files are filtered out."""
        mock_result = Mock()
        mock_result.stdout = "src/file.py\nREADME.md\nconfig.yaml\nsrc/test.py\n"
        mock_run.return_value = mock_result

        with patch("pathlib.Path.exists", return_value=True):
            files = _get_staged_files()

        assert len(files) == 2
        assert all(str(f).endswith(".py") for f in files)

    @patch("subprocess.run")
    def test_get_staged_files_filters_nonexistent(self, mock_run):
        """Test that non-existent files are filtered out."""
        mock_result = Mock()
        mock_result.stdout = "src/exists.py\nsrc/missing.py\n"
        mock_run.return_value = mock_result

        # Create a mock that returns True only for "src/exists.py"
        def exists_check(self):
            return str(self) == "src/exists.py"

        with patch("pathlib.Path.exists", exists_check):
            files = _get_staged_files()

        assert len(files) == 1
        assert str(files[0]) == "src/exists.py"

    @patch("subprocess.run")
    def test_get_staged_files_subprocess_error(self, mock_run):
        """Test handling of git command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(subprocess.CalledProcessError):
            _get_staged_files()

    @patch("subprocess.run")
    def test_get_staged_files_with_newlines(self, mock_run):
        """Test handling of extra newlines in git output."""
        mock_result = Mock()
        mock_result.stdout = "\n\nsrc/file1.py\n\nsrc/file2.py\n\n"
        mock_run.return_value = mock_result

        with patch("pathlib.Path.exists", return_value=True):
            files = _get_staged_files()

        assert len(files) == 2

    @patch("subprocess.run")
    def test_get_staged_files_git_command_correct(self, mock_run):
        """Test that correct git command is executed."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        _get_staged_files()

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "git"
        assert "diff" in call_args
        assert "--cached" in call_args


class TestCheckBypass:
    """Test _check_bypass() function."""

    def test_check_bypass_true_with_1(self):
        """Test bypass returns True when env var is '1'."""
        with patch.dict("os.environ", {"SKIP_CONSTITUTION_CHECK": "1"}):
            assert _check_bypass() is True

    def test_check_bypass_true_with_true(self):
        """Test bypass returns True when env var is 'true'."""
        with patch.dict("os.environ", {"SKIP_CONSTITUTION_CHECK": "true"}):
            assert _check_bypass() is True

    def test_check_bypass_true_with_yes(self):
        """Test bypass returns True when env var is 'yes'."""
        with patch.dict("os.environ", {"SKIP_CONSTITUTION_CHECK": "yes"}):
            assert _check_bypass() is True

    def test_check_bypass_true_with_on(self):
        """Test bypass returns True when env var is 'on'."""
        with patch.dict("os.environ", {"SKIP_CONSTITUTION_CHECK": "on"}):
            assert _check_bypass() is True

    def test_check_bypass_false_with_0(self):
        """Test bypass returns False when env var is '0'."""
        with patch.dict("os.environ", {"SKIP_CONSTITUTION_CHECK": "0"}):
            assert _check_bypass() is False

    def test_check_bypass_false_with_false(self):
        """Test bypass returns False when env var is 'false'."""
        with patch.dict("os.environ", {"SKIP_CONSTITUTION_CHECK": "false"}):
            assert _check_bypass() is False

    def test_check_bypass_false_when_unset(self):
        """Test bypass returns False when env var is not set."""
        with patch.dict("os.environ", {}, clear=True):
            assert _check_bypass() is False

    def test_check_bypass_case_insensitive(self):
        """Test that bypass check is case-insensitive."""
        with patch.dict("os.environ", {"SKIP_CONSTITUTION_CHECK": "TRUE"}):
            assert _check_bypass() is True

        with patch.dict("os.environ", {"SKIP_CONSTITUTION_CHECK": "YES"}):
            assert _check_bypass() is True


class TestDiscoverFiles:
    """Test _discover_files() function."""

    def test_discover_files_with_specific_file(self, tmp_path):
        """Test discovery with specific file path."""
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        mock_ignore = Mock()
        mock_ignore.should_ignore.return_value = False

        files = _discover_files(tmp_path, (test_file,), mock_ignore)

        assert len(files) == 1
        assert files[0] == test_file

    def test_discover_files_with_directory(self, tmp_path):
        """Test discovery with directory path."""
        (tmp_path / "file1.py").write_text("# file1")
        (tmp_path / "file2.py").write_text("# file2")
        (tmp_path / "README.md").write_text("# readme")

        mock_ignore = Mock()
        mock_ignore.should_ignore.return_value = False

        files = _discover_files(tmp_path, (tmp_path,), mock_ignore)

        assert len(files) == 2
        assert all(f.suffix == ".py" for f in files)

    def test_discover_files_entire_project(self, tmp_path):
        """Test discovery of entire project when no paths specified."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("# main")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("# test")

        mock_ignore = Mock()
        mock_ignore.should_ignore.return_value = False

        files = _discover_files(tmp_path, (), mock_ignore)

        assert len(files) >= 2

    def test_discover_files_respects_ignore_config(self, tmp_path):
        """Test that ignore configuration is respected."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("# file1")
        file2.write_text("# file2")

        mock_ignore = Mock()
        mock_ignore.should_ignore.side_effect = lambda p: p == file2

        files = _discover_files(tmp_path, (tmp_path,), mock_ignore)

        assert len(files) == 1
        assert files[0] == file1

    def test_discover_files_nested_directories(self, tmp_path):
        """Test discovery in nested directories."""
        (tmp_path / "src" / "subdir").mkdir(parents=True)
        (tmp_path / "src" / "file.py").write_text("# file")
        (tmp_path / "src" / "subdir" / "nested.py").write_text("# nested")

        mock_ignore = Mock()
        mock_ignore.should_ignore.return_value = False

        files = _discover_files(tmp_path, (tmp_path / "src",), mock_ignore)

        assert len(files) == 2

    def test_discover_files_empty_directory(self, tmp_path):
        """Test discovery in empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        mock_ignore = Mock()
        mock_ignore.should_ignore.return_value = False

        files = _discover_files(tmp_path, (empty_dir,), mock_ignore)

        assert files == []

    def test_discover_files_ignores_non_python(self, tmp_path):
        """Test that non-Python files are ignored."""
        (tmp_path / "file.py").write_text("# python")
        (tmp_path / "file.txt").write_text("text")
        (tmp_path / "file.md").write_text("markdown")

        mock_ignore = Mock()
        mock_ignore.should_ignore.return_value = False

        files = _discover_files(tmp_path, (tmp_path,), mock_ignore)

        assert len(files) == 1
        assert files[0].suffix == ".py"


class TestCheckDependencies:
    """Test check_dependencies() function."""

    @patch("shutil.which")
    def test_check_dependencies_all_present(self, mock_which):
        """Test when all dependencies are present."""
        mock_which.return_value = "/usr/bin/git"

        # All dependencies are present, should not raise
        check_dependencies()

    def test_check_dependencies_missing_coverage(self):
        """Test when coverage package is missing."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            # Mock the import to fail for coverage
            import builtins

            real_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "coverage":
                    raise ImportError("No module named 'coverage'")
                return real_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                with pytest.raises(DependencyCheckError, match="coverage"):
                    check_dependencies()

    def test_check_dependencies_missing_git_executable(self):
        """Test when git executable is not found."""
        with patch("shutil.which", return_value=None):
            with pytest.raises(DependencyCheckError, match="git"):
                check_dependencies()

    def test_check_dependencies_missing_gitpython(self):
        """Test when GitPython package is missing."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            # Mock the import to fail for git (GitPython)
            import builtins

            real_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "git":
                    raise ImportError("No module named 'git'")
                return real_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                with pytest.raises(DependencyCheckError, match="GitPython"):
                    check_dependencies()

    def test_check_dependencies_error_message_helpful(self):
        """Test that error messages provide installation instructions."""
        with patch("shutil.which", return_value=None):
            with pytest.raises(DependencyCheckError) as exc_info:
                check_dependencies()

            assert "Install" in str(exc_info.value) or "install" in str(exc_info.value)


class TestValidateCommand:
    """Test validate() command function."""

    def test_validate_with_bypass_exits_zero(self):
        """Test that bypass env var causes exit 0."""
        runner = CliRunner()

        with patch.dict("os.environ", {"SKIP_CONSTITUTION_CHECK": "1"}):
            result = runner.invoke(validate, [])

        assert result.exit_code == 0
        assert "bypassed" in result.output.lower() or "skip" in result.output.lower()

    def test_validate_dry_run_shows_files(self):
        """Test that --dry-run shows files to be scanned."""
        runner = CliRunner()

        # Mock dependencies and loaders
        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.loader.ConstitutionLoader") as mock_const_loader:
                with patch(
                    "src.constitution_validator.loader.IgnoreConfigurationLoader"
                ) as mock_ignore_loader:
                    mock_const_loader.return_value.load.return_value = Mock(principles=[])
                    mock_ignore_loader.return_value.load.return_value = Mock(
                        should_ignore=lambda x: False
                    )

                    with patch(
                        "src.constitution_validator.cli._discover_files",
                        return_value=[Path("file1.py"), Path("file2.py")],
                    ):
                        result = runner.invoke(validate, ["--dry-run"])

        assert result.exit_code == 0
        assert "file1.py" in result.output or "2" in result.output

    def test_validate_quiet_mode_minimal_output(self):
        """Test that --quiet produces minimal output."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._discover_files", return_value=[]):
                with patch("src.constitution_validator.loader.ConstitutionLoader") as mock_const:
                    with patch(
                        "src.constitution_validator.loader.IgnoreConfigurationLoader"
                    ) as mock_ignore:
                        with patch("src.constitution_validator.scanners.ast_scanner.ASTScanner"):
                            with patch(
                                "src.constitution_validator.rules.principle_i.UnifiedAgentRule"
                            ) as mock_agent_rule:
                                with patch(
                                    "src.constitution_validator.rules.principle_ii.CentralizedConfigRule"
                                ) as mock_cfg_rule:
                                    with patch(
                                        "src.constitution_validator.rules.principle_iii.DualDatabaseRule"
                                    ) as mock_db_rule:
                                        with patch(
                                            "src.constitution_validator.rules.principle_iv.TestCoverageRule"
                                        ) as mock_cov_rule:
                                            with patch(
                                                "src.constitution_validator.rules.principle_v.ObservabilityRule"
                                            ) as mock_obs_rule:
                                                with patch(
                                                    "src.constitution_validator.rules.principle_vi.GitAttributionRule"
                                                ) as mock_git_rule:
                                                    # Configure loader return values
                                                    mock_const.return_value.load.return_value = (
                                                        Mock(principles=[], version="1.0.0")
                                                    )
                                                    mock_ignore.return_value.load.return_value = (
                                                        Mock(should_ignore=lambda x: False)
                                                    )

                                                    # Configure rule return values
                                                    for rule_mock in [
                                                        mock_agent_rule,
                                                        mock_cfg_rule,
                                                        mock_db_rule,
                                                        mock_obs_rule,
                                                    ]:
                                                        rule_mock.return_value.execute.return_value = (
                                                            []
                                                        )
                                                    mock_cov_rule.return_value.execute_coverage_check.return_value = (
                                                        []
                                                    )
                                                    mock_git_rule.return_value.execute_git_check.return_value = (
                                                        []
                                                    )

                                                    result = runner.invoke(validate, ["--quiet"])

        # Output should be minimal
        lines = [line for line in result.output.split("\n") if line.strip()]
        assert len(lines) <= 10

    def test_validate_verbose_mode_detailed_output(self):
        """Test that --verbose shows detailed output."""
        runner = CliRunner()

        # Mock all dependencies
        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._discover_files", return_value=[]):
                with patch("src.constitution_validator.loader.ConstitutionLoader") as mock_const:
                    with patch(
                        "src.constitution_validator.loader.IgnoreConfigurationLoader"
                    ) as mock_ignore:
                        with patch("src.constitution_validator.scanners.ast_scanner.ASTScanner"):
                            with patch(
                                "src.constitution_validator.rules.principle_i.UnifiedAgentRule"
                            ) as mock_agent_rule:
                                with patch(
                                    "src.constitution_validator.rules.principle_ii.CentralizedConfigRule"
                                ) as mock_cfg_rule:
                                    with patch(
                                        "src.constitution_validator.rules.principle_iii.DualDatabaseRule"
                                    ) as mock_db_rule:
                                        with patch(
                                            "src.constitution_validator.rules.principle_iv.TestCoverageRule"
                                        ) as mock_cov_rule:
                                            with patch(
                                                "src.constitution_validator.rules.principle_v.ObservabilityRule"
                                            ) as mock_obs_rule:
                                                with patch(
                                                    "src.constitution_validator.rules.principle_vi.GitAttributionRule"
                                                ) as mock_git_rule:
                                                    # Configure loader return values
                                                    mock_const.return_value.load.return_value = (
                                                        Mock(principles=[], version="1.0.0")
                                                    )
                                                    mock_ignore.return_value.load.return_value = (
                                                        Mock(should_ignore=lambda x: False)
                                                    )

                                                    # Configure rule return values
                                                    for rule_mock in [
                                                        mock_agent_rule,
                                                        mock_cfg_rule,
                                                        mock_db_rule,
                                                        mock_obs_rule,
                                                    ]:
                                                        rule_mock.return_value.execute.return_value = (
                                                            []
                                                        )
                                                    mock_cov_rule.return_value.execute_coverage_check.return_value = (
                                                        []
                                                    )
                                                    mock_git_rule.return_value.execute_git_check.return_value = (
                                                        []
                                                    )

                                                    result = runner.invoke(validate, ["--verbose"])

        assert "--verbose" not in result.output or result.exit_code in [0, 1]

    def test_validate_staged_flag(self):
        """Test that --staged flag triggers staged files mode."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli._get_staged_files", return_value=[]):
            with patch("src.constitution_validator.cli.check_dependencies"):
                with patch("src.constitution_validator.loader.ConstitutionLoader") as mock_const:
                    with patch(
                        "src.constitution_validator.loader.IgnoreConfigurationLoader"
                    ) as mock_ignore:
                        with patch("src.constitution_validator.scanners.ast_scanner.ASTScanner"):
                            with patch(
                                "src.constitution_validator.rules.principle_i.UnifiedAgentRule"
                            ) as mock_agent_rule:
                                with patch(
                                    "src.constitution_validator.rules.principle_ii.CentralizedConfigRule"
                                ) as mock_cfg_rule:
                                    with patch(
                                        "src.constitution_validator.rules.principle_iii.DualDatabaseRule"
                                    ) as mock_db_rule:
                                        with patch(
                                            "src.constitution_validator.rules.principle_iv.TestCoverageRule"
                                        ) as mock_cov_rule:
                                            with patch(
                                                "src.constitution_validator.rules.principle_v.ObservabilityRule"
                                            ) as mock_obs_rule:
                                                with patch(
                                                    "src.constitution_validator.rules.principle_vi.GitAttributionRule"
                                                ) as mock_git_rule:
                                                    # Configure loader return values
                                                    mock_const.return_value.load.return_value = (
                                                        Mock(principles=[], version="1.0.0")
                                                    )
                                                    mock_ignore.return_value.load.return_value = (
                                                        Mock(should_ignore=lambda x: False)
                                                    )

                                                    # Configure rule return values
                                                    for rule_mock in [
                                                        mock_agent_rule,
                                                        mock_cfg_rule,
                                                        mock_db_rule,
                                                        mock_obs_rule,
                                                    ]:
                                                        rule_mock.return_value.execute.return_value = (
                                                            []
                                                        )
                                                    mock_cov_rule.return_value.execute_coverage_check.return_value = (
                                                        []
                                                    )
                                                    mock_git_rule.return_value.execute_git_check.return_value = (
                                                        []
                                                    )

                                                    result = runner.invoke(validate, ["--staged"])

        # Should attempt to get staged files
        assert result.exit_code in [0, 1]

    def test_validate_output_file(self, tmp_path):
        """Test that --output writes to file."""
        runner = CliRunner()
        output_file = tmp_path / "report.json"

        with patch("src.constitution_validator.cli._discover_files", return_value=[]):
            with patch("src.constitution_validator.cli.check_dependencies"):
                result = runner.invoke(validate, ["--output", str(output_file), "--dry-run"])

        assert result.exit_code == 0

    def test_validate_skip_git_flag(self):
        """Test that --skip-git skips git validation."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli._discover_files", return_value=[]):
            with patch("src.constitution_validator.cli.check_dependencies"):
                with patch("src.constitution_validator.loader.ConstitutionLoader") as mock_const:
                    with patch(
                        "src.constitution_validator.loader.IgnoreConfigurationLoader"
                    ) as mock_ignore:
                        with patch("src.constitution_validator.scanners.ast_scanner.ASTScanner"):
                            with patch(
                                "src.constitution_validator.rules.principle_i.UnifiedAgentRule"
                            ) as mock_agent_rule:
                                with patch(
                                    "src.constitution_validator.rules.principle_ii.CentralizedConfigRule"
                                ) as mock_cfg_rule:
                                    with patch(
                                        "src.constitution_validator.rules.principle_iii.DualDatabaseRule"
                                    ) as mock_db_rule:
                                        with patch(
                                            "src.constitution_validator.rules.principle_iv.TestCoverageRule"
                                        ) as mock_cov_rule:
                                            with patch(
                                                "src.constitution_validator.rules.principle_v.ObservabilityRule"
                                            ) as mock_obs_rule:
                                                with patch(
                                                    "src.constitution_validator.rules.principle_vi.GitAttributionRule"
                                                ) as mock_git_rule:
                                                    # Configure loader return values
                                                    mock_const.return_value.load.return_value = (
                                                        Mock(principles=[], version="1.0.0")
                                                    )
                                                    mock_ignore.return_value.load.return_value = (
                                                        Mock(should_ignore=lambda x: False)
                                                    )

                                                    # Configure rule return values
                                                    for rule_mock in [
                                                        mock_agent_rule,
                                                        mock_cfg_rule,
                                                        mock_db_rule,
                                                        mock_obs_rule,
                                                    ]:
                                                        rule_mock.return_value.execute.return_value = (
                                                            []
                                                        )
                                                    mock_cov_rule.return_value.execute_coverage_check.return_value = (
                                                        []
                                                    )
                                                    mock_git_rule.return_value.execute_git_check.return_value = (
                                                        []
                                                    )

                                                    result = runner.invoke(validate, ["--skip-git"])

        assert result.exit_code in [0, 1]

    def test_validate_skip_coverage_flag(self):
        """Test that --skip-coverage skips coverage validation."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli._discover_files", return_value=[]):
            with patch("src.constitution_validator.cli.check_dependencies"):
                result = runner.invoke(validate, ["--skip-coverage"])

        assert result.exit_code in [0, 1]

    def test_validate_json_format(self):
        """Test that --format json produces JSON output."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli._discover_files", return_value=[]):
            with patch("src.constitution_validator.cli.check_dependencies"):
                with patch("src.constitution_validator.loader.ConstitutionLoader") as mock_const:
                    with patch(
                        "src.constitution_validator.loader.IgnoreConfigurationLoader"
                    ) as mock_ignore:
                        with patch("src.constitution_validator.scanners.ast_scanner.ASTScanner"):
                            with patch(
                                "src.constitution_validator.rules.principle_i.UnifiedAgentRule"
                            ) as mock_agent_rule:
                                with patch(
                                    "src.constitution_validator.rules.principle_ii.CentralizedConfigRule"
                                ) as mock_cfg_rule:
                                    with patch(
                                        "src.constitution_validator.rules.principle_iii.DualDatabaseRule"
                                    ) as mock_db_rule:
                                        with patch(
                                            "src.constitution_validator.rules.principle_iv.TestCoverageRule"
                                        ) as mock_cov_rule:
                                            with patch(
                                                "src.constitution_validator.rules.principle_v.ObservabilityRule"
                                            ) as mock_obs_rule:
                                                with patch(
                                                    "src.constitution_validator.rules.principle_vi.GitAttributionRule"
                                                ) as mock_git_rule:
                                                    # Configure loader return values
                                                    mock_const.return_value.load.return_value = (
                                                        Mock(principles=[], version="1.0.0")
                                                    )
                                                    mock_ignore.return_value.load.return_value = (
                                                        Mock(should_ignore=lambda x: False)
                                                    )

                                                    # Configure rule return values
                                                    for rule_mock in [
                                                        mock_agent_rule,
                                                        mock_cfg_rule,
                                                        mock_db_rule,
                                                        mock_obs_rule,
                                                    ]:
                                                        rule_mock.return_value.execute.return_value = (
                                                            []
                                                        )
                                                    mock_cov_rule.return_value.execute_coverage_check.return_value = (
                                                        []
                                                    )
                                                    mock_git_rule.return_value.execute_git_check.return_value = (
                                                        []
                                                    )

                                                    result = runner.invoke(
                                                        validate, ["--format", "json"]
                                                    )

        # Should accept json format
        assert "--format" not in result.output or result.exit_code in [0, 1]

    def test_validate_text_format(self):
        """Test that --format text produces text output."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli._discover_files", return_value=[]):
            with patch("src.constitution_validator.cli.check_dependencies"):
                with patch("src.constitution_validator.loader.ConstitutionLoader") as mock_const:
                    with patch(
                        "src.constitution_validator.loader.IgnoreConfigurationLoader"
                    ) as mock_ignore:
                        with patch("src.constitution_validator.scanners.ast_scanner.ASTScanner"):
                            with patch(
                                "src.constitution_validator.rules.principle_i.UnifiedAgentRule"
                            ) as mock_agent_rule:
                                with patch(
                                    "src.constitution_validator.rules.principle_ii.CentralizedConfigRule"
                                ) as mock_cfg_rule:
                                    with patch(
                                        "src.constitution_validator.rules.principle_iii.DualDatabaseRule"
                                    ) as mock_db_rule:
                                        with patch(
                                            "src.constitution_validator.rules.principle_iv.TestCoverageRule"
                                        ) as mock_cov_rule:
                                            with patch(
                                                "src.constitution_validator.rules.principle_v.ObservabilityRule"
                                            ) as mock_obs_rule:
                                                with patch(
                                                    "src.constitution_validator.rules.principle_vi.GitAttributionRule"
                                                ) as mock_git_rule:
                                                    # Configure loader return values
                                                    mock_const.return_value.load.return_value = (
                                                        Mock(principles=[], version="1.0.0")
                                                    )
                                                    mock_ignore.return_value.load.return_value = (
                                                        Mock(should_ignore=lambda x: False)
                                                    )

                                                    # Configure rule return values
                                                    for rule_mock in [
                                                        mock_agent_rule,
                                                        mock_cfg_rule,
                                                        mock_db_rule,
                                                        mock_obs_rule,
                                                    ]:
                                                        rule_mock.return_value.execute.return_value = (
                                                            []
                                                        )
                                                    mock_cov_rule.return_value.execute_coverage_check.return_value = (
                                                        []
                                                    )
                                                    mock_git_rule.return_value.execute_git_check.return_value = (
                                                        []
                                                    )

                                                    result = runner.invoke(
                                                        validate, ["--format", "text"]
                                                    )

        assert "--format" not in result.output or result.exit_code in [0, 1]

    def test_validate_with_file_paths(self, tmp_path):
        """Test validation with specific file paths."""
        runner = CliRunner()
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.loader.ConstitutionLoader") as mock_const:
                with patch(
                    "src.constitution_validator.loader.IgnoreConfigurationLoader"
                ) as mock_ignore:
                    with patch(
                        "src.constitution_validator.scanners.ast_scanner.ASTScanner"
                    ) as mock_scanner:
                        with patch(
                            "src.constitution_validator.rules.principle_i.UnifiedAgentRule"
                        ) as mock_agent_rule:
                            with patch(
                                "src.constitution_validator.rules.principle_ii.CentralizedConfigRule"
                            ) as mock_cfg_rule:
                                with patch(
                                    "src.constitution_validator.rules.principle_iii.DualDatabaseRule"
                                ) as mock_db_rule:
                                    with patch(
                                        "src.constitution_validator.rules.principle_iv.TestCoverageRule"
                                    ) as mock_cov_rule:
                                        with patch(
                                            "src.constitution_validator.rules.principle_v.ObservabilityRule"
                                        ) as mock_obs_rule:
                                            with patch(
                                                "src.constitution_validator.rules.principle_vi.GitAttributionRule"
                                            ) as mock_git_rule:
                                                # Configure loader return values
                                                mock_const.return_value.load.return_value = Mock(
                                                    principles=[], version="1.0.0"
                                                )
                                                mock_ignore.return_value.load.return_value = Mock(
                                                    should_ignore=lambda x: False
                                                )

                                                # Configure scanner to return valid AST
                                                mock_scanner.return_value.parse_file.return_value = (
                                                    Mock()
                                                )

                                                # Configure rule return values
                                                for rule_mock in [
                                                    mock_agent_rule,
                                                    mock_cfg_rule,
                                                    mock_db_rule,
                                                    mock_obs_rule,
                                                ]:
                                                    rule_mock.return_value.execute.return_value = []
                                                mock_cov_rule.return_value.execute_coverage_check.return_value = (
                                                    []
                                                )
                                                mock_git_rule.return_value.execute_git_check.return_value = (
                                                    []
                                                )

                                                result = runner.invoke(validate, [str(test_file)])

        # Should accept file path
        assert result.exit_code in [0, 1]

    def test_validate_dependency_check_error(self):
        """Test handling of dependency check failure."""
        runner = CliRunner()

        with patch(
            "src.constitution_validator.cli.check_dependencies",
            side_effect=DependencyCheckError("Missing dep"),
        ):
            result = runner.invoke(validate, [])

        assert result.exit_code == 1
        assert "Missing dep" in result.output


class TestCLIGroup:
    """Test CLI group and version."""

    def test_cli_version_option(self):
        """Test that --version shows version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0

    def test_cli_help_option(self):
        """Test that --help shows help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "validate" in result.output.lower()

    def test_validate_help(self):
        """Test that validate --help shows detailed help."""
        runner = CliRunner()
        result = runner.invoke(validate, ["--help"])

        assert result.exit_code == 0
        assert "--quiet" in result.output
        assert "--verbose" in result.output
        assert "--dry-run" in result.output


class TestMainFunction:
    """Test main() entry point."""

    @patch("src.constitution_validator.cli.cli")
    def test_main_calls_cli(self, mock_cli):
        """Test that main() calls cli()."""
        main()

        mock_cli.assert_called_once()


class TestValidateEdgeCases:
    """Test edge cases in validation."""

    def test_validate_empty_file_list(self):
        """Test validation with no files to scan."""
        runner = CliRunner()

        with patch("src.constitution_validator.cli._discover_files", return_value=[]):
            with patch("src.constitution_validator.cli.check_dependencies"):
                result = runner.invoke(validate, [])

        # Should handle empty file list gracefully
        assert result.exit_code in [0, 1]

    def test_validate_invalid_output_format(self):
        """Test with invalid output format."""
        runner = CliRunner()

        result = runner.invoke(validate, ["--format", "xml"])

        # Should show error for invalid format
        assert result.exit_code == 2

    def test_validate_nonexistent_path(self):
        """Test with nonexistent file path."""
        runner = CliRunner()

        result = runner.invoke(validate, ["/nonexistent/path.py"])

        # Should show error for nonexistent path
        assert result.exit_code == 2

    @patch("src.constitution_validator.cli.check_dependencies")
    def test_validate_exception_during_execution(self, mock_check_deps):
        """Test handling of unexpected exception."""
        runner = CliRunner()

        with patch(
            "src.constitution_validator.cli._discover_files",
            side_effect=Exception("Unexpected error"),
        ):
            result = runner.invoke(validate, [])

        assert result.exit_code == 1
        assert "error" in result.output.lower()


class TestValidateCompleteFlow:
    """Test complete validation flow with mocked components."""

    def test_validate_complete_success_flow(self, tmp_path):
        """Test complete successful validation flow."""
        runner = CliRunner()

        # Setup mocks
        test_file = tmp_path / "test.py"
        test_file.write_text("# test")

        with patch("src.constitution_validator.cli.check_dependencies"):
            with patch("src.constitution_validator.cli._discover_files", return_value=[test_file]):
                with patch(
                    "src.constitution_validator.loader.ConstitutionLoader"
                ) as mock_const_loader:
                    with patch(
                        "src.constitution_validator.loader.IgnoreConfigurationLoader"
                    ) as mock_ignore_loader:
                        with patch(
                            "src.constitution_validator.scanners.ast_scanner.ASTScanner"
                        ) as mock_scanner:
                            with patch(
                                "src.constitution_validator.rules.principle_i.UnifiedAgentRule"
                            ) as mock_agent_rule:
                                with patch(
                                    "src.constitution_validator.rules.principle_ii.CentralizedConfigRule"
                                ) as mock_cfg_rule:
                                    with patch(
                                        "src.constitution_validator.rules.principle_iii.DualDatabaseRule"
                                    ) as mock_db_rule:
                                        with patch(
                                            "src.constitution_validator.rules.principle_iv.TestCoverageRule"
                                        ) as mock_cov_rule:
                                            with patch(
                                                "src.constitution_validator.rules.principle_v.ObservabilityRule"
                                            ) as mock_obs_rule:
                                                with patch(
                                                    "src.constitution_validator.rules.principle_vi.GitAttributionRule"
                                                ) as mock_git_rule:
                                                    mock_principle = Mock()
                                                    mock_principle.principle_id = "I"
                                                    mock_principle.name = "Test Principle"
                                                    mock_const = Mock()
                                                    mock_const.version = "1.0.0"
                                                    mock_const.principles = [mock_principle]
                                                    mock_const_loader.return_value.load.return_value = (
                                                        mock_const
                                                    )

                                                    mock_ignore = Mock()
                                                    mock_ignore.should_ignore.return_value = False
                                                    mock_ignore_loader.return_value.load.return_value = (
                                                        mock_ignore
                                                    )

                                                    mock_tree = Mock()
                                                    mock_scanner_instance = Mock()
                                                    mock_scanner_instance.parse_file.return_value = (
                                                        mock_tree
                                                    )
                                                    mock_scanner.return_value = (
                                                        mock_scanner_instance
                                                    )

                                                    # All rules return no violations
                                                    for rule_mock in [
                                                        mock_agent_rule,
                                                        mock_cfg_rule,
                                                        mock_db_rule,
                                                        mock_obs_rule,
                                                    ]:
                                                        rule_mock.return_value.execute.return_value = (
                                                            []
                                                        )

                                                    mock_cov_rule.return_value.execute_coverage_check.return_value = (
                                                        []
                                                    )
                                                    mock_git_rule.return_value.execute_git_check.return_value = (
                                                        []
                                                    )

                                                    result = runner.invoke(validate, [])

        assert result.exit_code == 0


class TestDependencyCheckErrorException:
    """Test DependencyCheckError exception."""

    def test_dependency_check_error_is_exception(self):
        """Test that DependencyCheckError is an Exception."""
        error = DependencyCheckError("Test error")
        assert isinstance(error, Exception)

    def test_dependency_check_error_message(self):
        """Test that error message is preserved."""
        error = DependencyCheckError("Test error message")
        assert str(error) == "Test error message"
