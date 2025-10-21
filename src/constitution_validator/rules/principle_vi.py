"""
Principle VI validation rule: Git Attribution Standards.

Detects AI attribution in git commit messages.
"""

import re
from pathlib import Path
from typing import List

from src.constitution_validator.models import (
    ViolationRecord,
    ViolationLocation,
    ConfidenceLevel,
)
from src.constitution_validator.rules.base import ValidationRule
from src.constitution_validator.scanners.git_scanner import GitScanner


class GitAttributionRule(ValidationRule):
    """Validates adherence to Git Attribution Standards principle."""

    def __init__(self):
        """Initialize the Git Attribution validation rule."""
        super().__init__(
            rule_id="CONST-VI-001",
            principle_id="VI",
            name="Detect AI attribution in commits",
            description="Detects AI attribution patterns in git commit messages",
            violation_message_template="AI attribution found in commit {commit}: {pattern}",
            remediation_guidance=(
                "Remove AI attribution from commit messages. "
                "All work should be attributed to the repository owner, not AI assistants. "
                "Use 'git commit --amend' to fix the most recent commit message, "
                "or 'git rebase -i' for older commits."
            ),
            confidence_level=ConfidenceLevel.HIGH,
            severity="error",
        )

        # Patterns to detect (case-insensitive)
        self.ai_patterns = [
            r"co-authored-by:\s*claude",
            r"co-authored-by:\s*anthropic",
            r"generated\s+with\s+claude",
            r"generated\s+with\s+\[claude\s+code\]",
            r"assisted\s+by\s+anthropic",
            r"assisted\s+by\s+claude",
            r"@anthropic\.com",
        ]

        self.git_scanner = GitScanner()

    def execute_git_check(self, project_root: Path) -> List[ViolationRecord]:
        """
        Execute git commit message check.

        Args:
            project_root: Root directory of the git repository

        Returns:
            List of violation records found
        """
        violations = []

        try:
            # Get unpushed commits
            commits = self.git_scanner.get_unpushed_commits(project_root)

            for commit in commits:
                # Skip merge commits (they can have multiple authors)
                if len(commit.parents) > 1:
                    continue

                # Check commit message against patterns
                for pattern in self.ai_patterns:
                    matches = re.finditer(pattern, commit.message, re.IGNORECASE)
                    for match in matches:
                        violation = ViolationRecord(
                            rule_id=self.rule_id,
                            principle_id=self.principle_id,
                            location=ViolationLocation(
                                file_path=project_root / ".git" / "HEAD",  # Symbolic location
                                line_number=1,
                            ),
                            message=self.violation_message_template.format(
                                commit=commit.hexsha[:8],
                                pattern=match.group(0)
                            ),
                            remediation=self.remediation_guidance,
                            confidence=self.confidence_level,
                            severity=self.severity,
                            detected_code=match.group(0),
                            suggested_fix=f"Remove '{match.group(0)}' from commit {commit.hexsha[:8]}",
                            metadata={
                                "commit_sha": commit.hexsha,
                                "commit_message": commit.message,
                            },
                        )

                        violations.append(violation)

        except Exception as e:
            # If git operations fail, we might not be in a git repo
            # Don't report this as a violation, just skip
            pass

        return violations
