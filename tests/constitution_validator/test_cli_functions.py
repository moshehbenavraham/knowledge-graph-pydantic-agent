"""
Comprehensive tests for src/constitution_validator/cli.py functions.

Tests CLI helper functions and utilities.
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.constitution_validator.cli import (
    _check_bypass,
    _discover_files,
    _get_staged_files,
)


class TestGetStagedFiles:
    """Test _get_staged_files function."""

    @patch("subprocess.run")
    def test_get_staged_files_success(self, mock_run):
        """Test successful retrieval of staged files."""
        mock_result = MagicMock()
        mock_result.stdout = "src/file1.py\nsrc/file2.py\ntests/test_file.py\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with patch("pathlib.Path.exists", return_value=True):
            files = _get_staged_files()

            assert len(files) == 3
            assert all(isinstance(f, Path) for f in files)
            assert all(str(f).endswith(".py") for f in files)

    @patch("subprocess.run")
    def test_get_staged_files_filters_python_only(self, mock_run):
        """Test only Python files are returned."""
        mock_result = MagicMock()
        mock_result.stdout = "src/file1.py\nREADME.md\nconfig.json\nsrc/file2.py\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with patch("pathlib.Path.exists", return_value=True):
            files = _get_staged_files()

            assert len(files) == 2
            assert all(str(f).endswith(".py") for f in files)

    @patch("subprocess.run")
    def test_get_staged_files_filters_nonexistent(self, mock_run):
        """Test non-existent files are filtered out."""
        mock_result = MagicMock()
        mock_result.stdout = "existing.py\nnonexistent.py\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        def mock_exists(self):
            return str(self) == "existing.py"

        with patch("pathlib.Path.exists", mock_exists):
            files = _get_staged_files()

            assert len(files) == 1
            assert str(files[0]) == "existing.py"

    @patch("subprocess.run")
    def test_get_staged_files_empty_result(self, mock_run):
        """Test when no files are staged."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        files = _get_staged_files()

        assert len(files) == 0

    @patch("subprocess.run")
    def test_get_staged_files_git_error(self, mock_run):
        """Test git command error handling."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(subprocess.CalledProcessError):
            _get_staged_files()

    @patch("subprocess.run")
    def test_get_staged_files_correct_git_command(self, mock_run):
        """Test correct git command is called."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        _get_staged_files()

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "git"
        assert "diff" in call_args
        assert "--cached" in call_args
        assert "--name-only" in call_args

    @patch("subprocess.run")
    def test_get_staged_files_handles_whitespace(self, mock_run):
        """Test handles files with whitespace in names."""
        mock_result = MagicMock()
        mock_result.stdout = "src/file with spaces.py\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with patch("pathlib.Path.exists", return_value=True):
            files = _get_staged_files()

            assert len(files) == 1
            assert "file with spaces.py" in str(files[0])


class TestCheckBypass:
    """Test _check_bypass function."""

    def test_check_bypass_false_by_default(self):
        """Test bypass is false by default."""
        with patch.dict(os.environ, {}, clear=True):
            assert _check_bypass() is False

    def test_check_bypass_with_1(self):
        """Test bypass with '1'."""
        with patch.dict(os.environ, {"SKIP_CONSTITUTION_CHECK": "1"}):
            assert _check_bypass() is True

    def test_check_bypass_with_true(self):
        """Test bypass with 'true'."""
        with patch.dict(os.environ, {"SKIP_CONSTITUTION_CHECK": "true"}):
            assert _check_bypass() is True

    def test_check_bypass_with_TRUE(self):
        """Test bypass with 'TRUE' (case insensitive)."""
        with patch.dict(os.environ, {"SKIP_CONSTITUTION_CHECK": "TRUE"}):
            assert _check_bypass() is True

    def test_check_bypass_with_yes(self):
        """Test bypass with 'yes'."""
        with patch.dict(os.environ, {"SKIP_CONSTITUTION_CHECK": "yes"}):
            assert _check_bypass() is True

    def test_check_bypass_with_on(self):
        """Test bypass with 'on'."""
        with patch.dict(os.environ, {"SKIP_CONSTITUTION_CHECK": "on"}):
            assert _check_bypass() is True

    def test_check_bypass_with_0(self):
        """Test bypass with '0' (false)."""
        with patch.dict(os.environ, {"SKIP_CONSTITUTION_CHECK": "0"}):
            assert _check_bypass() is False

    def test_check_bypass_with_false(self):
        """Test bypass with 'false'."""
        with patch.dict(os.environ, {"SKIP_CONSTITUTION_CHECK": "false"}):
            assert _check_bypass() is False

    def test_check_bypass_with_no(self):
        """Test bypass with 'no'."""
        with patch.dict(os.environ, {"SKIP_CONSTITUTION_CHECK": "no"}):
            assert _check_bypass() is False

    def test_check_bypass_with_random_value(self):
        """Test bypass with random value."""
        with patch.dict(os.environ, {"SKIP_CONSTITUTION_CHECK": "random"}):
            assert _check_bypass() is False

    def test_check_bypass_with_empty_string(self):
        """Test bypass with empty string."""
        with patch.dict(os.environ, {"SKIP_CONSTITUTION_CHECK": ""}):
            assert _check_bypass() is False


class TestDiscoverFiles:
    """Test _discover_files function."""

    def test_discover_files_single_file(self, tmp_path):
        """Test discovering single Python file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        mock_ignore = MagicMock()
        mock_ignore.should_ignore.return_value = False

        files = _discover_files(tmp_path, (test_file,), mock_ignore)

        assert len(files) == 1
        assert files[0] == test_file

    def test_discover_files_directory(self, tmp_path):
        """Test discovering files in directory."""
        # Create structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "file1.py").write_text("# file1")
        (src_dir / "file2.py").write_text("# file2")

        mock_ignore = MagicMock()
        mock_ignore.should_ignore.return_value = False

        files = _discover_files(tmp_path, (src_dir,), mock_ignore)

        assert len(files) == 2
        assert all(f.suffix == ".py" for f in files)

    def test_discover_files_recursive(self, tmp_path):
        """Test recursive directory discovery."""
        # Create nested structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "top.py").write_text("# top")

        sub_dir = src_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "nested.py").write_text("# nested")

        mock_ignore = MagicMock()
        mock_ignore.should_ignore.return_value = False

        files = _discover_files(tmp_path, (src_dir,), mock_ignore)

        assert len(files) == 2
        assert any("top.py" in str(f) for f in files)
        assert any("nested.py" in str(f) for f in files)

    def test_discover_files_filters_ignored(self, tmp_path):
        """Test ignored files are filtered."""
        test_file1 = tmp_path / "included.py"
        test_file1.write_text("# included")
        test_file2 = tmp_path / "excluded.py"
        test_file2.write_text("# excluded")

        mock_ignore = MagicMock()
        mock_ignore.should_ignore.side_effect = lambda path: "excluded" in str(path)

        files = _discover_files(tmp_path, (tmp_path,), mock_ignore)

        assert len(files) == 1
        assert files[0] == test_file1

    def test_discover_files_no_target_paths(self, tmp_path):
        """Test discovering all files when no target paths."""
        (tmp_path / "file1.py").write_text("# file1")
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "file2.py").write_text("# file2")

        mock_ignore = MagicMock()
        mock_ignore.should_ignore.return_value = False

        files = _discover_files(tmp_path, (), mock_ignore)

        assert len(files) >= 2

    def test_discover_files_non_python_excluded(self, tmp_path):
        """Test non-Python files are excluded."""
        (tmp_path / "script.py").write_text("# python")
        (tmp_path / "README.md").write_text("# readme")
        (tmp_path / "config.json").write_text("{}")

        mock_ignore = MagicMock()
        mock_ignore.should_ignore.return_value = False

        files = _discover_files(tmp_path, (tmp_path,), mock_ignore)

        assert len(files) == 1
        assert files[0].suffix == ".py"

    def test_discover_files_multiple_target_paths(self, tmp_path):
        """Test multiple target paths."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        (dir1 / "file1.py").write_text("# file1")

        dir2 = tmp_path / "dir2"
        dir2.mkdir()
        (dir2 / "file2.py").write_text("# file2")

        mock_ignore = MagicMock()
        mock_ignore.should_ignore.return_value = False

        files = _discover_files(tmp_path, (dir1, dir2), mock_ignore)

        assert len(files) == 2

    def test_discover_files_empty_directory(self, tmp_path):
        """Test empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        mock_ignore = MagicMock()
        mock_ignore.should_ignore.return_value = False

        files = _discover_files(tmp_path, (empty_dir,), mock_ignore)

        assert len(files) == 0

    def test_discover_files_mixed_file_and_dir(self, tmp_path):
        """Test mix of file and directory paths."""
        file1 = tmp_path / "standalone.py"
        file1.write_text("# standalone")

        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        (dir1 / "nested.py").write_text("# nested")

        mock_ignore = MagicMock()
        mock_ignore.should_ignore.return_value = False

        files = _discover_files(tmp_path, (file1, dir1), mock_ignore)

        assert len(files) == 2


class TestEdgeCases:
    """Test edge cases."""

    @patch("subprocess.run")
    def test_get_staged_files_with_special_chars_in_names(self, mock_run):
        """Test files with special characters in names."""
        mock_result = MagicMock()
        mock_result.stdout = "src/file_name-123.py\nsrc/file.name.py\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with patch("pathlib.Path.exists", return_value=True):
            files = _get_staged_files()

            assert len(files) == 2

    def test_check_bypass_with_mixed_case(self):
        """Test bypass check is case-insensitive."""
        with patch.dict(os.environ, {"SKIP_CONSTITUTION_CHECK": "TrUe"}):
            assert _check_bypass() is True

    def test_discover_files_symlinks(self, tmp_path):
        """Test handling of symlinks."""
        real_file = tmp_path / "real.py"
        real_file.write_text("# real")

        # Note: symlink support varies by platform
        try:
            link_file = tmp_path / "link.py"
            link_file.symlink_to(real_file)

            mock_ignore = MagicMock()
            mock_ignore.should_ignore.return_value = False

            files = _discover_files(tmp_path, (tmp_path,), mock_ignore)

            # Should discover at least the real file
            assert len(files) >= 1
        except OSError:
            # Skip if symlinks not supported
            pytest.skip("Symlinks not supported on this platform")

    def test_discover_files_permission_error(self, tmp_path):
        """Test handling of permission errors."""
        restricted_dir = tmp_path / "restricted"
        restricted_dir.mkdir()
        (restricted_dir / "file.py").write_text("# file")

        mock_ignore = MagicMock()
        mock_ignore.should_ignore.return_value = False

        # Try to make directory unreadable (may not work on all platforms)
        try:
            restricted_dir.chmod(0o000)
            files = _discover_files(tmp_path, (tmp_path,), mock_ignore)
            # Should handle gracefully
            assert isinstance(files, list)
        finally:
            # Restore permissions for cleanup
            restricted_dir.chmod(0o755)

    def test_discover_files_very_deep_nesting(self, tmp_path):
        """Test very deep directory nesting."""
        current = tmp_path
        for i in range(10):
            current = current / f"level{i}"
            current.mkdir()
        (current / "deep.py").write_text("# deep")

        mock_ignore = MagicMock()
        mock_ignore.should_ignore.return_value = False

        files = _discover_files(tmp_path, (tmp_path,), mock_ignore)

        assert len(files) == 1
        assert "deep.py" in str(files[0])


class TestFunctionIntegration:
    """Test integration between functions."""

    @patch("subprocess.run")
    def test_staged_files_can_be_discovered(self, mock_run, tmp_path):
        """Test that staged files can be properly discovered."""
        # Create test files
        test_file = tmp_path / "staged.py"
        test_file.write_text("# staged")

        # Mock git to return this file
        mock_result = MagicMock()
        mock_result.stdout = str(test_file) + "\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Get staged files
        with patch("pathlib.Path.exists", return_value=True):
            staged_files = _get_staged_files()

        # Verify discovery works
        mock_ignore = MagicMock()
        mock_ignore.should_ignore.return_value = False

        discovered_files = _discover_files(tmp_path, tuple(staged_files), mock_ignore)

        assert len(discovered_files) > 0

    def test_bypass_check_environment_isolated(self):
        """Test bypass check doesn't affect other environment variables."""
        original_env = dict(os.environ)

        with patch.dict(os.environ, {"SKIP_CONSTITUTION_CHECK": "1", "OTHER_VAR": "value"}):
            _check_bypass()

        # Environment should be restored (or isolated)
        assert os.environ.get("OTHER_VAR") == original_env.get("OTHER_VAR")
