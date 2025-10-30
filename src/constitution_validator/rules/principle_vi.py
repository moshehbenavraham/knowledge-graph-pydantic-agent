"""
Principle VI validation rule: Git Attribution Standards.

Detects AI attribution in git commit messages.
"""

import ast
from pathlib import Path

import structlog

from src.constitution_validator.models import (
    ConfidenceLevel,
    ViolationRecord,
)
from src.constitution_validator.rules.base import BaseValidationRule

logger = structlog.get_logger(__name__)


class GitAttributionRule(BaseValidationRule):
    """Validates adherence to Git Attribution Standards principle."""

    rule_id = "CONST-VI-001"
    principle_id = "VI"
    rule_name = "Detect AI attribution in commits"

    def execute(
        self, tree: ast.AST, file_path: Path, source_code: str | None = None
    ) -> list[ViolationRecord]:
        """
        Execute validation on git commits (not AST-based).

        Note: This rule checks git commit messages, not Python AST.
        The tree parameter is kept for API consistency.

        Args:
            tree: Parsed AST (not used for git validation)
            file_path: Path to file (used to locate git repository)
            source_code: Optional source code (for tests or when file doesn't exist)

        Returns:
            List of violations detected
        """
        logger.info("Executing Principle VI rule", rule_id=self.rule_id, file=str(file_path))
        # Prepare instance state
        self._prepare_execution(file_path, tree, source_code)

        try:
            import re

            from git import Repo

            # Find git repository
            repo = Repo(file_path.parent, search_parent_directories=True)

            # Check recent commits (unpushed commits)
            try:
                commits = list(repo.iter_commits("origin/main..HEAD", max_count=100))
            except Exception:
                # Fallback to all commits if origin/main doesn't exist
                commits = list(repo.iter_commits("HEAD", max_count=20))

            # Patterns to detect
            prohibited_patterns = [
                r"Co-Authored-By:.*Claude",
                r"Generated with.*Claude Code",
                r"Co-Authored-By:.*noreply@anthropic\.com",
                r"\bAnthropic\b",
            ]

            for commit in commits:
                message = commit.message

                # Skip merge commits
                if len(commit.parents) > 1:
                    continue

                # Ensure hexsha and summary are strings (decode if bytes)
                hexsha_str = commit.hexsha.decode() if isinstance(commit.hexsha, bytes) else commit.hexsha
                summary_str = commit.summary.decode() if isinstance(commit.summary, bytes) else commit.summary

                for pattern in prohibited_patterns:
                    if re.search(pattern, message, re.IGNORECASE):
                        self.add_violation(
                            line_number=1,  # Git commits don't have line numbers
                            message=f"AI attribution detected in commit {hexsha_str[:7]}: {summary_str[:50]}",
                            remediation=(
                                "Remove AI attribution from commit message.\n"
                                "All work should be attributed to the repository owner.\n"
                                "Use: git commit --amend to fix the message."
                            ),
                            detected_code=summary_str,
                            suggested_fix="# Remove Claude/Anthropic attribution",
                            confidence=ConfidenceLevel.HIGH,
                            severity="error",
                            metadata={"commit_sha": hexsha_str, "pattern": pattern},
                        )
                        break  # Only report once per commit

        except Exception:  # nosec B110 - Git operations may fail for non-git files
            # Git operations failed - this is okay, not all files are in git
            pass

        logger.info(
            "Principle VI rule completed", rule_id=self.rule_id, violations=len(self.violations)
        )
        return self.violations

    def execute_git_check(self, repo_path: Path) -> list[ViolationRecord]:
        """
        Execute git commit check (test compatibility method).

        Args:
            repo_path: Path to git repository

        Returns:
            List of violations detected
        """
        logger.info("Executing git attribution check", repo_path=str(repo_path))
        import re

        from src.constitution_validator.scanners.git_scanner import GitScanner

        self.violations = []
        self.file_path = repo_path

        try:
            scanner = GitScanner()
            commits = scanner.get_unpushed_commits(repo_path)
            logger.info("Commits retrieved", count=len(commits))

            # Prohibited attribution patterns
            prohibited_patterns = [
                r"co-authored-by:\s*claude",
                r"generated\s+with\s+claude\s+code",
                r"claude\s+code",
                r"@anthropic\.com",
                r"anthropic",
            ]

            for commit in commits:
                # Skip merge commits
                is_merge = getattr(commit, "is_merge", False) or (
                    hasattr(commit, "parents") and len(commit.parents) > 1
                )
                if is_merge:
                    continue

                message = commit.message if hasattr(commit, "message") else str(commit)
                hexsha = commit.hexsha if hasattr(commit, "hexsha") else "unknown"

                # Ensure hexsha and message are strings (decode if bytes)
                hexsha_str = hexsha.decode() if isinstance(hexsha, bytes) else hexsha
                message_str = message.decode() if isinstance(message, bytes) else message

                # Check for prohibited patterns
                for pattern in prohibited_patterns:
                    if re.search(pattern, message_str, re.IGNORECASE):
                        self.add_violation(
                            line_number=1,
                            message=f"AI attribution detected in commit {hexsha_str[:7]}: {message_str[:50].strip()}",
                            remediation=(
                                "Remove AI attribution from commit message.\n"
                                "All work should be attributed to the repository owner.\n"
                                "Use: git commit --amend to fix the message."
                            ),
                            detected_code=message_str[:100],
                            suggested_fix="# Remove Claude/Anthropic attribution",
                            confidence=ConfidenceLevel.HIGH,
                            severity="error",
                            metadata={"commit_sha": hexsha_str, "pattern": pattern},
                        )
                        break  # Only report once per commit

        except Exception:  # nosec B110 - Git operations may fail
            # Git operations failed - this is okay
            pass

        return self.violations


# No alias needed - GitAttributionRule is the expected name
