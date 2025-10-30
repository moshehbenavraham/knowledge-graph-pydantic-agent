"""
Git repository scanner.

Scans git commit messages for attribution violations.
"""

from pathlib import Path
from typing import Any

import structlog

try:
    from git import Commit, GitCommandError, InvalidGitRepositoryError, Repo

    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    Commit = Any  # type: ignore

logger = structlog.get_logger()


class GitScanner:
    """Scanner for git repository operations."""

    def __init__(self):
        """Initialize git scanner."""
        logger.debug("Initializing GitScanner", git_available=GIT_AVAILABLE)
        if not GIT_AVAILABLE:
            logger.warning(
                "gitpython_not_available",
                message="GitPython not installed - git checks will be skipped",
            )

    def get_unpushed_commits(self, repo_path: Path) -> list[Commit]:
        """
        Get list of commits that haven't been pushed to remote.

        Args:
            repo_path: Path to the git repository root

        Returns:
            List of unpushed Commit objects

        Raises:
            Exception: If not a git repository or git operations fail
        """
        logger.info("Getting unpushed commits", repo_path=str(repo_path))
        if not GIT_AVAILABLE:
            logger.warning("git_check_skipped", reason="GitPython not installed")
            return []

        try:
            repo = Repo(repo_path)

            # Get the current branch
            if repo.head.is_detached:
                logger.warning("detached_head", message="Repository is in detached HEAD state")
                return []

            current_branch = repo.active_branch

            # Get remote tracking branch
            try:
                tracking_branch = current_branch.tracking_branch()
                if tracking_branch is None:
                    # No remote tracking branch - check all commits
                    logger.info(
                        "no_tracking_branch",
                        message="No remote tracking branch, checking all commits",
                    )
                    commits = list(repo.iter_commits(current_branch.name, max_count=100))
                    return commits
            except Exception:
                # No tracking branch configured
                commits = list(repo.iter_commits(current_branch.name, max_count=100))
                return commits

            # Get commits that are ahead of remote
            try:
                unpushed_commits = list(
                    repo.iter_commits(f"{tracking_branch.name}..{current_branch.name}")
                )
                logger.info("unpushed_commits_found", count=len(unpushed_commits))
                return unpushed_commits

            except GitCommandError as e:
                logger.warning("git_command_failed", error=str(e))
                return []

        except InvalidGitRepositoryError:
            logger.warning("not_a_git_repository", path=str(repo_path))
            return []

        except Exception as e:
            logger.error("git_scanner_error", error=str(e), exc_info=True)
            return []

    def is_merge_commit(self, commit: Commit) -> bool:
        """
        Check if a commit is a merge commit.

        Args:
            commit: Git commit object

        Returns:
            True if commit has multiple parents (is a merge)
        """
        logger.debug("Checking if commit is merge", commit_sha=commit.hexsha[:7])
        is_merge = len(commit.parents) > 1
        logger.debug("Merge check complete", is_merge=is_merge)
        return is_merge

    def get_commit_message(self, commit: Commit) -> str:
        """
        Get the full commit message.

        Args:
            commit: Git commit object

        Returns:
            Full commit message including body
        """
        logger.debug("Getting commit message", commit_sha=commit.hexsha[:7])
        message = commit.message
        logger.debug("Commit message retrieved", length=len(message))
        return message
