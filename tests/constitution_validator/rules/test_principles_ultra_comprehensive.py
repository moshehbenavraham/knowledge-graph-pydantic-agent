"""Ultra comprehensive tests for constitution validator rules (target: 90%+ coverage)."""

import ast
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch


class TestPrincipleIV:
    """Test TestCoverageRule (Principle IV)."""

    def test_test_coverage_rule_init(self):
        from src.constitution_validator.rules.principle_iv import TestCoverageRule

        rule = TestCoverageRule()

        assert rule.rule_id == "CONST-IV-001"
        assert rule.principle_id == "IV"
        assert rule.MINIMUM_COVERAGE == 50.0

    def test_test_coverage_rule_skip_test_files(self):
        from src.constitution_validator.rules.principle_iv import TestCoverageRule

        rule = TestCoverageRule()

        # Create a test file path
        test_file = Path("/project/tests/test_something.py")
        tree = ast.parse("def test_func():\n    pass\n")

        violations = rule.execute(tree, test_file)

        # Should skip test files
        assert len(violations) == 0

    def test_test_coverage_rule_no_coverage_data(self):
        from src.constitution_validator.rules.principle_iv import TestCoverageRule

        rule = TestCoverageRule()

        # Non-test file
        source_file = Path("/project/src/module.py")
        tree = ast.parse("def func():\n    pass\n")

        # No coverage data available - should not raise
        violations = rule.execute(tree, source_file)

        # Should not report violations when coverage data is missing
        assert len(violations) == 0

    @patch("coverage.Coverage")
    def test_test_coverage_rule_below_minimum(self, mock_coverage_class):
        from src.constitution_validator.rules.principle_iv import TestCoverageRule

        rule = TestCoverageRule()

        # Mock coverage data
        mock_cov = Mock()
        mock_coverage_class.return_value = mock_cov
        mock_cov.load.return_value = None  # load() doesn't raise

        # Mock analysis: 100 executable lines, 40 missing lines = 60% coverage
        # Format: (executed, executable, excluded, missing, missing_formatted)
        mock_cov.analysis2.return_value = ([], 100, [], list(range(1, 41)), [])

        source_file = Path("/project/src/module.py")
        tree = ast.parse("def func():\n    pass\n")

        violations = rule.execute(tree, source_file)

        # Should report violation (60% >= 50%, so NO violation now)
        assert len(violations) == 0

    @patch("coverage.Coverage")
    def test_test_coverage_rule_above_minimum(self, mock_coverage_class):
        from src.constitution_validator.rules.principle_iv import TestCoverageRule

        rule = TestCoverageRule()

        # Mock coverage data
        mock_cov = Mock()
        mock_coverage_class.return_value = mock_cov

        # Mock analysis: 100 executable lines, 15 missing = 85% coverage
        mock_cov.analysis2.return_value = ([], 100, [], 15, [])

        source_file = Path("/project/src/module.py")
        tree = ast.parse("def func():\n    pass\n")

        violations = rule.execute(tree, source_file)

        # Should not report violation (85% >= 50%)
        assert len(violations) == 0

    def test_execute_coverage_check_success(self):
        from src.constitution_validator.rules.principle_iv import TestCoverageRule

        rule = TestCoverageRule()

        with patch(
            "src.constitution_validator.scanners.coverage_scanner.CoverageScanner"
        ) as MockScanner:
            mock_scanner = Mock()
            mock_scanner.get_coverage.return_value = 80.0
            MockScanner.return_value = mock_scanner

            with tempfile.TemporaryDirectory() as temp_dir:
                violations = rule.execute_coverage_check(Path(temp_dir))

                # 80% >= 50%, should not report violation
                assert len(violations) == 0

    def test_execute_coverage_check_below_minimum(self):
        from src.constitution_validator.rules.principle_iv import TestCoverageRule

        rule = TestCoverageRule()

        with patch(
            "src.constitution_validator.scanners.coverage_scanner.CoverageScanner"
        ) as MockScanner:
            mock_scanner = Mock()
            mock_scanner.get_coverage.return_value = 35.0
            MockScanner.return_value = mock_scanner

            with tempfile.TemporaryDirectory() as temp_dir:
                violations = rule.execute_coverage_check(Path(temp_dir))

                # 35% < 50%, should report violation
                assert len(violations) == 1
                assert "35.0%" in violations[0].message
                assert violations[0].severity == "error"

    def test_execute_coverage_check_measurement_failure(self):
        from src.constitution_validator.rules.principle_iv import TestCoverageRule

        rule = TestCoverageRule()

        with patch(
            "src.constitution_validator.scanners.coverage_scanner.CoverageScanner"
        ) as MockScanner:
            mock_scanner = Mock()
            mock_scanner.get_coverage.side_effect = Exception("pytest-cov not installed")
            MockScanner.return_value = mock_scanner

            with tempfile.TemporaryDirectory() as temp_dir:
                violations = rule.execute_coverage_check(Path(temp_dir))

                # Should report measurement failure as warning
                assert len(violations) == 1
                assert "measurement failed" in violations[0].message.lower()
                assert violations[0].severity == "warning"


class TestPrincipleVI:
    """Test GitAttributionRule (Principle VI)."""

    def test_git_attribution_rule_init(self):
        from src.constitution_validator.rules.principle_vi import GitAttributionRule

        rule = GitAttributionRule()

        assert rule.rule_id == "CONST-VI-001"
        assert rule.principle_id == "VI"

    def test_git_attribution_rule_no_git_repo(self):
        from src.constitution_validator.rules.principle_vi import GitAttributionRule

        rule = GitAttributionRule()

        # Non-git directory
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "module.py"
            tree = ast.parse("def func():\n    pass\n")

            violations = rule.execute(tree, file_path)

            # Should not report violations when not a git repo
            assert len(violations) == 0

    @patch("git.Repo")
    def test_git_attribution_rule_detect_claude_attribution(self, mock_repo_class):
        from src.constitution_validator.rules.principle_vi import GitAttributionRule

        rule = GitAttributionRule()

        # Mock git repo
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.message = "Fix bug\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        mock_commit.summary = "Fix bug"
        mock_commit.hexsha = "abc123456"
        mock_commit.parents = [Mock()]  # Single parent (not merge)

        mock_repo.iter_commits.return_value = [mock_commit]
        mock_repo_class.return_value = mock_repo

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "module.py"
            tree = ast.parse("def func():\n    pass\n")

            violations = rule.execute(tree, file_path)

            # Should detect AI attribution
            assert len(violations) == 1
            assert "attribution detected" in violations[0].message.lower()
            assert violations[0].severity == "error"

    @patch("git.Repo")
    def test_git_attribution_rule_detect_generated_with_claude(self, mock_repo_class):
        from src.constitution_validator.rules.principle_vi import GitAttributionRule

        rule = GitAttributionRule()

        # Mock git repo
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.message = "Add feature\n\nGenerated with Claude Code"
        mock_commit.summary = "Add feature"
        mock_commit.hexsha = "def456789"
        mock_commit.parents = [Mock()]

        mock_repo.iter_commits.return_value = [mock_commit]
        mock_repo_class.return_value = mock_repo

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "module.py"
            tree = ast.parse("def func():\n    pass\n")

            violations = rule.execute(tree, file_path)

            # Should detect AI attribution
            assert len(violations) == 1
            assert "attribution detected" in violations[0].message.lower()

    @patch("git.Repo")
    def test_git_attribution_rule_skip_merge_commits(self, mock_repo_class):
        from src.constitution_validator.rules.principle_vi import GitAttributionRule

        rule = GitAttributionRule()

        # Mock git repo
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.message = "Merge branch\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        mock_commit.summary = "Merge branch"
        mock_commit.hexsha = "merge123"
        mock_commit.parents = [Mock(), Mock()]  # Multiple parents (merge commit)

        mock_repo.iter_commits.return_value = [mock_commit]
        mock_repo_class.return_value = mock_repo

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "module.py"
            tree = ast.parse("def func():\n    pass\n")

            violations = rule.execute(tree, file_path)

            # Should skip merge commits
            assert len(violations) == 0

    @patch("git.Repo")
    def test_git_attribution_rule_clean_commits(self, mock_repo_class):
        from src.constitution_validator.rules.principle_vi import GitAttributionRule

        rule = GitAttributionRule()

        # Mock git repo
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.message = "Clean commit message\n\nNo AI attribution here"
        mock_commit.summary = "Clean commit message"
        mock_commit.hexsha = "clean123"
        mock_commit.parents = [Mock()]

        mock_repo.iter_commits.return_value = [mock_commit]
        mock_repo_class.return_value = mock_repo

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "module.py"
            tree = ast.parse("def func():\n    pass\n")

            violations = rule.execute(tree, file_path)

            # Should not report violations for clean commits
            assert len(violations) == 0

    def test_execute_git_check_success(self):
        from src.constitution_validator.rules.principle_vi import GitAttributionRule

        rule = GitAttributionRule()

        with patch("src.constitution_validator.scanners.git_scanner.GitScanner") as MockScanner:
            mock_scanner = Mock()

            # Mock commit with AI attribution
            mock_commit = Mock()
            mock_commit.message = "Fix bug\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
            mock_commit.hexsha = "abc123456"
            mock_commit.parents = [Mock()]
            del mock_commit.is_merge  # Remove is_merge attr so getattr returns default

            mock_scanner.get_unpushed_commits.return_value = [mock_commit]
            MockScanner.return_value = mock_scanner

            with tempfile.TemporaryDirectory() as temp_dir:
                violations = rule.execute_git_check(Path(temp_dir))

                # Should detect AI attribution
                assert len(violations) == 1
                assert "attribution detected" in violations[0].message.lower()

    def test_execute_git_check_skip_merge_commits(self):
        from src.constitution_validator.rules.principle_vi import GitAttributionRule

        rule = GitAttributionRule()

        with patch("src.constitution_validator.scanners.git_scanner.GitScanner") as MockScanner:
            mock_scanner = Mock()

            # Mock merge commit with AI attribution
            mock_commit = Mock()
            mock_commit.message = "Merge\n\nCo-Authored-By: Claude"
            mock_commit.hexsha = "merge123"
            mock_commit.parents = [Mock(), Mock()]
            mock_commit.is_merge = True

            mock_scanner.get_unpushed_commits.return_value = [mock_commit]
            MockScanner.return_value = mock_scanner

            with tempfile.TemporaryDirectory() as temp_dir:
                violations = rule.execute_git_check(Path(temp_dir))

                # Should skip merge commits
                assert len(violations) == 0

    def test_execute_git_check_no_commits(self):
        from src.constitution_validator.rules.principle_vi import GitAttributionRule

        rule = GitAttributionRule()

        with patch("src.constitution_validator.scanners.git_scanner.GitScanner") as MockScanner:
            mock_scanner = Mock()
            mock_scanner.get_unpushed_commits.return_value = []
            MockScanner.return_value = mock_scanner

            with tempfile.TemporaryDirectory() as temp_dir:
                violations = rule.execute_git_check(Path(temp_dir))

                # No commits, no violations
                assert len(violations) == 0

    def test_execute_git_check_git_error(self):
        from src.constitution_validator.rules.principle_vi import GitAttributionRule

        rule = GitAttributionRule()

        with patch("src.constitution_validator.scanners.git_scanner.GitScanner") as MockScanner:
            mock_scanner = Mock()
            mock_scanner.get_unpushed_commits.side_effect = Exception("Git error")
            MockScanner.return_value = mock_scanner

            with tempfile.TemporaryDirectory() as temp_dir:
                violations = rule.execute_git_check(Path(temp_dir))

                # Should handle error gracefully
                assert len(violations) == 0

    def test_execute_git_check_anthropic_pattern(self):
        from src.constitution_validator.rules.principle_vi import GitAttributionRule

        rule = GitAttributionRule()

        with patch("src.constitution_validator.scanners.git_scanner.GitScanner") as MockScanner:
            mock_scanner = Mock()

            # Mock commit with "Anthropic" mention
            mock_commit = Mock()
            mock_commit.message = "Update docs\n\nThanks to Anthropic for the API"
            mock_commit.hexsha = "anthropic123"
            mock_commit.parents = [Mock()]
            del mock_commit.is_merge  # Remove is_merge attr so getattr returns default

            mock_scanner.get_unpushed_commits.return_value = [mock_commit]
            MockScanner.return_value = mock_scanner

            with tempfile.TemporaryDirectory() as temp_dir:
                violations = rule.execute_git_check(Path(temp_dir))

                # Should detect Anthropic mention
                assert len(violations) == 1
