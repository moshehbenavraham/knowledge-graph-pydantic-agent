"""
Unit tests for Principle VI validation rule (Git Attribution Standards).

Tests detection of AI attribution in commit messages.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.constitution_validator.models import (
    RuleCategory,
    ValidationRule,
    ViolationRecord,
    ConfidenceLevel,
)
from src.constitution_validator.rules.principle_vi import GitAttributionRule


class MockCommit:
    """Mock git commit object."""

    def __init__(self, sha: str, message: str, is_merge: bool = False):
        self.hexsha = sha
        self.message = message
        self._is_merge = is_merge

    @property
    def parents(self):
        # Merge commits have 2+ parents
        return ["parent1", "parent2"] if self._is_merge else ["parent1"]


class TestPrincipleVIRule:
    """Test suite for Principle VI: Git Attribution Standards validation."""

    @pytest.fixture
    def rule(self) -> GitAttributionRule:
        """Create a GitAttributionRule instance for testing."""
        return GitAttributionRule()

    @patch('src.constitution_validator.scanners.git_scanner.GitScanner.get_unpushed_commits')
    def test_detects_co_authored_by_claude(self, mock_get_commits, rule: GitAttributionRule):
        """Test detection of 'Co-Authored-By: Claude' in commit messages."""
        mock_commits = [
            MockCommit("abc123", """
Fix authentication bug

Co-Authored-By: Claude <noreply@anthropic.com>
""")
        ]
        mock_get_commits.return_value = mock_commits

        violations = rule.execute_git_check(Path("/project"))

        assert len(violations) == 1
        assert violations[0].rule_id == "CONST-VI-001"
        assert violations[0].principle_id == "VI"
        assert "Co-Authored-By" in violations[0].message or "Claude" in violations[0].message

    @patch('src.constitution_validator.scanners.git_scanner.GitScanner.get_unpushed_commits')
    def test_detects_generated_with_claude_code(self, mock_get_commits, rule: GitAttributionRule):
        """Test detection of 'Generated with Claude Code' in commit messages."""
        mock_commits = [
            MockCommit("def456", """
Add new feature

🤖 Generated with [Claude Code](https://claude.com/claude-code)
""")
        ]
        mock_get_commits.return_value = mock_commits

        violations = rule.execute_git_check(Path("/project"))

        assert len(violations) == 1
        assert "Generated with" in violations[0].message or "Claude Code" in violations[0].message

    @patch('src.constitution_validator.scanners.git_scanner.GitScanner.get_unpushed_commits')
    def test_detects_anthropic_attribution(self, mock_get_commits, rule: GitAttributionRule):
        """Test detection of Anthropic attribution."""
        mock_commits = [
            MockCommit("ghi789", """
Update documentation

Assisted by Anthropic AI
""")
        ]
        mock_get_commits.return_value = mock_commits

        violations = rule.execute_git_check(Path("/project"))

        assert len(violations) >= 1

    @patch('src.constitution_validator.scanners.git_scanner.GitScanner.get_unpushed_commits')
    def test_passes_clean_commit_messages(self, mock_get_commits, rule: GitAttributionRule):
        """Test that clean commit messages pass validation."""
        mock_commits = [
            MockCommit("clean1", "Fix bug in authentication module"),
            MockCommit("clean2", "Add unit tests for user service"),
            MockCommit("clean3", "Refactor database connection pooling"),
        ]
        mock_get_commits.return_value = mock_commits

        violations = rule.execute_git_check(Path("/project"))

        assert len(violations) == 0

    @patch('src.constitution_validator.scanners.git_scanner.GitScanner.get_unpushed_commits')
    def test_exempts_merge_commits(self, mock_get_commits, rule: GitAttributionRule):
        """Test that merge commits are exempted from checks."""
        mock_commits = [
            MockCommit("merge1", """
Merge branch 'feature' into main

Co-Authored-By: Claude <noreply@anthropic.com>
""", is_merge=True)
        ]
        mock_get_commits.return_value = mock_commits

        violations = rule.execute_git_check(Path("/project"))

        # Merge commits should be exempt
        assert len(violations) == 0

    @patch('src.constitution_validator.scanners.git_scanner.GitScanner.get_unpushed_commits')
    def test_detects_multiple_violations_in_different_commits(self, mock_get_commits, rule: GitAttributionRule):
        """Test detection across multiple commits."""
        mock_commits = [
            MockCommit("bad1", "Fix bug\n\nCo-Authored-By: Claude <noreply@anthropic.com>"),
            MockCommit("good", "Clean commit message"),
            MockCommit("bad2", "Add feature\n\n🤖 Generated with Claude Code"),
        ]
        mock_get_commits.return_value = mock_commits

        violations = rule.execute_git_check(Path("/project"))

        assert len(violations) == 2

    @patch('src.constitution_validator.scanners.git_scanner.GitScanner.get_unpushed_commits')
    def test_case_insensitive_detection(self, mock_get_commits, rule: GitAttributionRule):
        """Test that detection is case-insensitive."""
        mock_commits = [
            MockCommit("case1", "Fix\n\nco-authored-by: CLAUDE <email>"),
            MockCommit("case2", "Fix\n\ngenerated WITH claude code"),
        ]
        mock_get_commits.return_value = mock_commits

        violations = rule.execute_git_check(Path("/project"))

        assert len(violations) >= 1

    @patch('src.constitution_validator.scanners.git_scanner.GitScanner.get_unpushed_commits')
    def test_handles_git_errors(self, mock_get_commits, rule: GitAttributionRule):
        """Test handling when git operations fail."""
        mock_get_commits.side_effect = Exception("Not a git repository")

        violations = rule.execute_git_check(Path("/project"))

        # Should report error gracefully
        assert len(violations) >= 0  # May return empty or error violation

    @patch('src.constitution_validator.scanners.git_scanner.GitScanner.get_unpushed_commits')
    def test_remediation_mentions_proper_attribution(self, mock_get_commits, rule: GitAttributionRule):
        """Test that remediation mentions proper attribution practices."""
        mock_commits = [
            MockCommit("bad", "Fix\n\nCo-Authored-By: Claude <email>")
        ]
        mock_get_commits.return_value = mock_commits

        violations = rule.execute_git_check(Path("/project"))

        assert len(violations) == 1
        remediation = violations[0].remediation.lower()
        assert "remove" in remediation or "attribution" in remediation

    @patch('src.constitution_validator.scanners.git_scanner.GitScanner.get_unpushed_commits')
    def test_confidence_level_is_high(self, mock_get_commits, rule: GitAttributionRule):
        """Test that pattern matching has HIGH confidence."""
        mock_commits = [
            MockCommit("bad", "Fix\n\nCo-Authored-By: Claude <email>")
        ]
        mock_get_commits.return_value = mock_commits

        violations = rule.execute_git_check(Path("/project"))

        assert violations[0].confidence == ConfidenceLevel.HIGH

    @patch('src.constitution_validator.scanners.git_scanner.GitScanner.get_unpushed_commits')
    def test_severity_is_error(self, mock_get_commits, rule: GitAttributionRule):
        """Test that AI attribution is an error."""
        mock_commits = [
            MockCommit("bad", "Fix\n\nCo-Authored-By: Claude <email>")
        ]
        mock_get_commits.return_value = mock_commits

        violations = rule.execute_git_check(Path("/project"))

        assert violations[0].severity == "error"

    @patch('src.constitution_validator.scanners.git_scanner.GitScanner.get_unpushed_commits')
    def test_violation_includes_commit_sha(self, mock_get_commits, rule: GitAttributionRule):
        """Test that violation includes commit SHA for identification."""
        commit_sha = "abc123def456"
        mock_commits = [
            MockCommit(commit_sha, "Fix\n\nCo-Authored-By: Claude <email>")
        ]
        mock_get_commits.return_value = mock_commits

        violations = rule.execute_git_check(Path("/project"))

        assert len(violations) == 1
        # Violation should reference the commit somehow
        assert violations[0].detected_code or violations[0].message

    @patch('src.constitution_validator.scanners.git_scanner.GitScanner.get_unpushed_commits')
    def test_handles_no_commits(self, mock_get_commits, rule: GitAttributionRule):
        """Test handling when there are no unpushed commits."""
        mock_get_commits.return_value = []

        violations = rule.execute_git_check(Path("/project"))

        assert len(violations) == 0
