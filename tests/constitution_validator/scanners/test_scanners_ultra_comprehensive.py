"""Ultra comprehensive tests for constitution validator scanners (target: 90%+ coverage)."""

import ast
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestASTScanner:
    """Test ASTScanner class."""

    def test_ast_scanner_init(self):
        from src.constitution_validator.scanners.ast_scanner import ASTScanner

        scanner = ASTScanner(cache_size=100)
        assert scanner.cache_size == 100
        assert len(scanner._parse_cache) == 0

    def test_ast_scanner_init_default_cache_size(self):
        from src.constitution_validator.scanners.ast_scanner import ASTScanner

        scanner = ASTScanner()
        assert scanner.cache_size == 1024

    def test_parse_file_success(self):
        from src.constitution_validator.scanners.ast_scanner import ASTScanner

        scanner = ASTScanner()

        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def hello():\n    return 'world'\n")
            temp_path = Path(f.name)

        try:
            tree = scanner.parse_file(temp_path)

            assert tree is not None
            assert isinstance(tree, ast.Module)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_parse_file_caching(self):
        from src.constitution_validator.scanners.ast_scanner import ASTScanner

        scanner = ASTScanner()

        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def hello():\n    return 'world'\n")
            temp_path = Path(f.name)

        try:
            # Parse the file twice
            tree1 = scanner.parse_file(temp_path)
            tree2 = scanner.parse_file(temp_path)

            # Should return the same cached tree
            assert tree1 is tree2
            assert len(scanner._parse_cache) == 1
        finally:
            temp_path.unlink(missing_ok=True)

    def test_parse_file_syntax_error(self):
        from src.constitution_validator.scanners.ast_scanner import ASTScanner

        scanner = ASTScanner()

        # Create a file with syntax error
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def hello(\n")  # Missing closing paren
            temp_path = Path(f.name)

        try:
            tree = scanner.parse_file(temp_path)

            assert tree is None
        finally:
            temp_path.unlink(missing_ok=True)

    def test_parse_file_encoding_error(self):
        from src.constitution_validator.scanners.ast_scanner import ASTScanner

        scanner = ASTScanner()

        # Create a file with invalid encoding
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".py", delete=False) as f:
            f.write(b"\xff\xfe")  # Invalid UTF-8
            temp_path = Path(f.name)

        try:
            tree = scanner.parse_file(temp_path)

            assert tree is None
        finally:
            temp_path.unlink(missing_ok=True)

    def test_parse_file_general_exception(self):
        from src.constitution_validator.scanners.ast_scanner import ASTScanner

        scanner = ASTScanner()

        with patch("builtins.open", side_effect=OSError("File read error")):
            tree = scanner.parse_file(Path("/fake/file.py"))

            assert tree is None

    def test_cache_eviction(self):
        from src.constitution_validator.scanners.ast_scanner import ASTScanner

        scanner = ASTScanner(cache_size=2)

        files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(f"def func{i}():\n    pass\n")
                files.append(Path(f.name))

        try:
            # Parse 3 files with cache size 2
            for file_path in files:
                scanner.parse_file(file_path)

            # Cache should contain only 2 entries (oldest evicted)
            assert len(scanner._parse_cache) == 2
        finally:
            for file_path in files:
                file_path.unlink(missing_ok=True)

    def test_clear_cache(self):
        from src.constitution_validator.scanners.ast_scanner import ASTScanner

        scanner = ASTScanner()

        # Create and parse a file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def hello():\n    pass\n")
            temp_path = Path(f.name)

        try:
            scanner.parse_file(temp_path)
            assert len(scanner._parse_cache) > 0

            scanner.clear_cache()
            assert len(scanner._parse_cache) == 0
        finally:
            temp_path.unlink(missing_ok=True)

    def test_get_cache_stats(self):
        from src.constitution_validator.scanners.ast_scanner import ASTScanner

        scanner = ASTScanner(cache_size=100)

        # Parse some files
        files = []
        for i in range(5):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(f"def func{i}():\n    pass\n")
                files.append(Path(f.name))

        try:
            for file_path in files:
                scanner.parse_file(file_path)

            stats = scanner.get_cache_stats()

            assert stats["cache_size"] == 5
            assert stats["cache_capacity"] == 100
            assert stats["cache_usage_percent"] == 5.0
        finally:
            for file_path in files:
                file_path.unlink(missing_ok=True)

    def test_hash_content(self):
        from src.constitution_validator.scanners.ast_scanner import ASTScanner

        scanner = ASTScanner()

        content1 = "def hello():\n    return 'world'\n"
        content2 = "def hello():\n    return 'world'\n"
        content3 = "def goodbye():\n    return 'world'\n"

        hash1 = scanner._hash_content(content1)
        hash2 = scanner._hash_content(content2)
        hash3 = scanner._hash_content(content3)

        # Same content should have same hash
        assert hash1 == hash2
        # Different content should have different hash
        assert hash1 != hash3


class TestCoverageScanner:
    """Test CoverageScanner class."""

    def test_coverage_scanner_init(self):
        from src.constitution_validator.scanners.coverage_scanner import CoverageScanner

        scanner = CoverageScanner()
        assert scanner.coverage_pattern is not None

    def test_parse_coverage_output_total_format(self):
        from src.constitution_validator.scanners.coverage_scanner import CoverageScanner

        scanner = CoverageScanner()

        output = """
        Name        Stmts   Miss  Cover
        -------------------------------
        src/main.py   100     25    75%
        TOTAL        1234    567    78%
        """

        coverage = scanner._parse_coverage_output(output)

        assert coverage == 78.0

    def test_parse_coverage_output_alt_format(self):
        from src.constitution_validator.scanners.coverage_scanner import CoverageScanner

        scanner = CoverageScanner()

        output = "Overall: 85.5% coverage"

        coverage = scanner._parse_coverage_output(output)

        assert coverage == 85.5

    def test_parse_coverage_output_not_found(self):
        from src.constitution_validator.scanners.coverage_scanner import CoverageScanner

        scanner = CoverageScanner()

        output = "No coverage information found"

        coverage = scanner._parse_coverage_output(output)

        assert coverage is None

    def test_check_pytest_cov_installed_success(self):
        from src.constitution_validator.scanners.coverage_scanner import CoverageScanner

        scanner = CoverageScanner()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="pytest 7.4.0")

            result = scanner.check_pytest_cov_installed()

            assert result is True

    def test_check_pytest_cov_installed_not_found(self):
        from src.constitution_validator.scanners.coverage_scanner import CoverageScanner

        scanner = CoverageScanner()

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = scanner.check_pytest_cov_installed()

            assert result is False

    def test_check_pytest_cov_installed_timeout(self):
        from src.constitution_validator.scanners.coverage_scanner import CoverageScanner

        scanner = CoverageScanner()

        with patch("subprocess.run", side_effect=Exception("Timeout")):
            result = scanner.check_pytest_cov_installed()

            assert result is False

    @patch("subprocess.run")
    def test_get_coverage_success(self, mock_run):
        from src.constitution_validator.scanners.coverage_scanner import CoverageScanner

        scanner = CoverageScanner()

        mock_run.return_value = Mock(stdout="TOTAL    1000    200    80%", stderr="", returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            coverage = scanner.get_coverage(Path(temp_dir))

            assert coverage == 80.0

    @patch("subprocess.run")
    def test_get_coverage_from_stderr(self, mock_run):
        from src.constitution_validator.scanners.coverage_scanner import CoverageScanner

        scanner = CoverageScanner()

        mock_run.return_value = Mock(stdout="", stderr="TOTAL    1000    150    85%", returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            coverage = scanner.get_coverage(Path(temp_dir))

            assert coverage == 85.0

    @patch("subprocess.run")
    def test_get_coverage_pytest_not_found(self, mock_run):
        from src.constitution_validator.scanners.coverage_scanner import CoverageScanner

        scanner = CoverageScanner()

        mock_run.side_effect = FileNotFoundError()

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(Exception, match="pytest not found"):
                scanner.get_coverage(Path(temp_dir))

    @patch("subprocess.run")
    def test_get_coverage_timeout(self, mock_run):
        import subprocess

        from src.constitution_validator.scanners.coverage_scanner import CoverageScanner

        scanner = CoverageScanner()

        mock_run.side_effect = subprocess.TimeoutExpired("pytest", 300)

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(Exception, match="timed out"):
                scanner.get_coverage(Path(temp_dir))

    @patch("subprocess.run")
    def test_get_coverage_parse_error(self, mock_run):
        from src.constitution_validator.scanners.coverage_scanner import CoverageScanner

        scanner = CoverageScanner()

        mock_run.return_value = Mock(stdout="No coverage info", stderr="", returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(Exception, match="Could not parse coverage"):
                scanner.get_coverage(Path(temp_dir))


class TestGitScanner:
    """Test GitScanner class."""

    def test_git_scanner_init_git_available(self):
        from src.constitution_validator.scanners.git_scanner import GitScanner

        scanner = GitScanner()
        assert scanner is not None

    def test_get_unpushed_commits_git_not_available(self):
        from src.constitution_validator.scanners.git_scanner import GitScanner

        scanner = GitScanner()

        with patch("src.constitution_validator.scanners.git_scanner.GIT_AVAILABLE", False):
            with tempfile.TemporaryDirectory() as temp_dir:
                commits = scanner.get_unpushed_commits(Path(temp_dir))

                assert commits == []

    def test_get_unpushed_commits_not_git_repo(self):
        from src.constitution_validator.scanners.git_scanner import GitScanner

        scanner = GitScanner()

        with tempfile.TemporaryDirectory() as temp_dir:
            commits = scanner.get_unpushed_commits(Path(temp_dir))

            assert commits == []

    def test_is_merge_commit(self):
        from src.constitution_validator.scanners.git_scanner import GitScanner

        scanner = GitScanner()

        # Mock commit with multiple parents
        mock_commit = Mock()
        mock_commit.parents = [Mock(), Mock()]

        assert scanner.is_merge_commit(mock_commit) is True

        # Mock commit with single parent
        mock_commit.parents = [Mock()]

        assert scanner.is_merge_commit(mock_commit) is False

    def test_get_commit_message(self):
        from src.constitution_validator.scanners.git_scanner import GitScanner

        scanner = GitScanner()

        mock_commit = Mock()
        mock_commit.message = "Test commit message\n\nDetailed description"

        message = scanner.get_commit_message(mock_commit)

        assert message == "Test commit message\n\nDetailed description"

    @patch("src.constitution_validator.scanners.git_scanner.Repo")
    def test_get_unpushed_commits_detached_head(self, mock_repo_class):
        from src.constitution_validator.scanners.git_scanner import GitScanner

        scanner = GitScanner()

        mock_repo = Mock()
        mock_repo.head.is_detached = True
        mock_repo_class.return_value = mock_repo

        with tempfile.TemporaryDirectory() as temp_dir:
            commits = scanner.get_unpushed_commits(Path(temp_dir))

            assert commits == []

    @patch("src.constitution_validator.scanners.git_scanner.Repo")
    def test_get_unpushed_commits_no_tracking_branch(self, mock_repo_class):
        from src.constitution_validator.scanners.git_scanner import GitScanner

        scanner = GitScanner()

        mock_repo = Mock()
        mock_repo.head.is_detached = False
        mock_branch = Mock()
        mock_branch.tracking_branch.return_value = None
        mock_branch.name = "main"
        mock_repo.active_branch = mock_branch

        mock_commit = Mock()
        mock_commit.hexsha = "abc123"
        mock_commit.message = "Test commit"
        mock_repo.iter_commits.return_value = [mock_commit]

        mock_repo_class.return_value = mock_repo

        with tempfile.TemporaryDirectory() as temp_dir:
            commits = scanner.get_unpushed_commits(Path(temp_dir))

            assert len(commits) == 1

    @patch("src.constitution_validator.scanners.git_scanner.Repo")
    def test_get_unpushed_commits_with_tracking_branch(self, mock_repo_class):
        from src.constitution_validator.scanners.git_scanner import GitScanner

        scanner = GitScanner()

        mock_repo = Mock()
        mock_repo.head.is_detached = False

        mock_tracking_branch = Mock()
        mock_tracking_branch.name = "origin/main"

        mock_branch = Mock()
        mock_branch.tracking_branch.return_value = mock_tracking_branch
        mock_branch.name = "main"
        mock_repo.active_branch = mock_branch

        mock_commit = Mock()
        mock_commit.hexsha = "abc123"
        mock_commit.message = "Unpushed commit"
        mock_repo.iter_commits.return_value = [mock_commit]

        mock_repo_class.return_value = mock_repo

        with tempfile.TemporaryDirectory() as temp_dir:
            commits = scanner.get_unpushed_commits(Path(temp_dir))

            assert len(commits) == 1
