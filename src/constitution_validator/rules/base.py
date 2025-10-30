"""
Base validation rule class with AST and regex utilities.

All principle-specific rules inherit from BaseValidationRule.
"""

import ast
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import structlog

from src.constitution_validator.models import (
    ConfidenceLevel,
    ViolationLocation,
    ViolationRecord,
)

logger = structlog.get_logger(__name__)


class BaseValidationRule(ABC):
    """
    Base class for all constitutional validation rules.

    Provides:
    - Abstract execute() method for validation logic
    - Violation creation utilities
    - Inline suppression support (# noqa: CONST-X-YYY)

    Usage:
        rule = SomeRule()
        violations = rule.execute(tree, file_path)
    """

    # Subclasses must define these
    rule_id: str = "CONST-X-001"
    principle_id: str = "X"
    rule_name: str = "Base Rule"

    def __init__(self):
        """Initialize base validation rule."""
        # Instance state reset on each execute() call
        self.violations: list[ViolationRecord] = []
        self.file_path: Path | None = None
        self.source_code: str = ""
        self.source_lines: list[str] = []

    @abstractmethod
    def execute(  # noqa: CONST-V-001 - Abstract method stub
        self, tree: ast.AST, file_path: Path, source_code: str | None = None
    ) -> list[ViolationRecord]:
        """
        Execute validation rule on AST and return violations.

        Subclasses MUST implement this method with their specific logic.

        Args:
            tree: Parsed AST of the file
            file_path: Path to the file being validated
            source_code: Optional source code (for tests or when file doesn't exist)

        Returns:
            List of detected violations
        """
        pass

    def _prepare_execution(
        self, file_path: Path, tree: ast.AST | None = None, source_code: str | None = None
    ):
        """
        Prepare instance state for execution.

        Args:
            file_path: Path to file being validated
            tree: Optional AST tree (used to extract source code if file doesn't exist)
            source_code: Optional source code (takes precedence over file/tree)
        """
        logger.debug("Preparing rule execution", rule_id=self.rule_id, file=str(file_path))
        self.violations = []
        self.file_path = file_path

        # Priority: explicit source_code > file contents > AST unparse
        if source_code:
            self.source_code = source_code
        elif file_path.exists():
            try:
                self.source_code = file_path.read_text()
            except Exception as e:
                logger.warning(f"Could not read file: {e}", file=str(file_path))
                self.source_code = ""
        elif tree is not None:
            # For tests: reconstruct source from AST (loses comments!)
            try:
                self.source_code = ast.unparse(tree)
            except Exception:
                self.source_code = ""
        else:
            self.source_code = ""

        self.source_lines = self.source_code.splitlines()
        logger.debug("Execution prepared", lines=len(self.source_lines))

    def add_violation(
        self,
        line_number: int,
        message: str,
        remediation: str,
        column_number: int | None = None,
        detected_code: str | None = None,
        suggested_fix: str | None = None,
        confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
        severity: str = "error",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add a violation with automatic suppression checking.

        Checks for inline # noqa: CONST-X-YYY comments.

        Args:
            line_number: Line where violation occurs
            message: Specific violation message
            remediation: How to fix this violation
            column_number: Optional column offset
            detected_code: Exact code that violated the rule
            suggested_fix: Suggested code replacement
            confidence: Detection confidence level
            severity: error, warning, or info
            metadata: Additional context
        """
        # Check for inline suppression
        suppressed, suppression_reason = self._check_suppression(line_number)

        location = ViolationLocation(
            file_path=self.file_path,
            line_number=line_number,
            column_number=column_number,
            context_lines=self._get_context_lines(line_number),
        )

        violation = ViolationRecord(
            rule_id=self.rule_id,
            principle_id=self.principle_id,
            location=location,
            message=message,
            remediation=remediation,
            confidence=confidence,
            severity=severity,
            detected_code=detected_code,
            suggested_fix=suggested_fix,
            metadata=metadata or {},
            suppressed=suppressed,
            suppression_reason=suppression_reason,
        )

        self.violations.append(violation)

        if suppressed:
            logger.debug(
                "Violation suppressed",
                rule_id=self.rule_id,
                file=str(self.file_path),
                line=line_number,
                reason=suppression_reason,
            )

    def _check_suppression(self, line_number: int) -> tuple[bool, str | None]:
        """
        Check if violation on this line is suppressed via # noqa comment.

        Supports formats:
        - # noqa: CONST-II-001
        - # noqa: CONST-II-001 - reason for suppression
        - # noqa: CONSTITUTION-II (principle-level suppression)

        Args:
            line_number: Line number to check (1-indexed)

        Returns:
            Tuple of (is_suppressed, suppression_reason)
        """
        logger.debug("Checking suppression", line_number=line_number, rule_id=self.rule_id)
        if line_number < 1 or line_number > len(self.source_lines):
            return False, None

        line = self.source_lines[line_number - 1]  # Convert to 0-indexed

        # Check for noqa comments: CONST-X-YYY or CONSTITUTION-X format
        noqa_pattern = r"#\s*noqa:\s*(CONST|CONSTITUTION)-([IVX]+)(?:-(\d+))?\s*(?:-\s*(.+))?"
        match = re.search(noqa_pattern, line, re.IGNORECASE)

        if not match:
            return False, None

        _prefix, principle_id, rule_number, reason = match.groups()

        # Check if suppression applies to this rule
        if principle_id != self.principle_id:
            return False, None

        # If specific rule number given, check it matches
        if rule_number:
            expected_rule_id = f"CONST-{principle_id}-{rule_number}"
            if expected_rule_id != self.rule_id:
                return False, None

        suppression_reason = reason.strip() if reason else "Suppressed via noqa comment"
        logger.debug("Suppression found", line_number=line_number, reason=suppression_reason)
        return True, suppression_reason

    def _get_context_lines(self, line_number: int, context: int = 2) -> str:
        """
        Get surrounding lines for context.

        Args:
            line_number: Center line (1-indexed)
            context: Number of lines before/after

        Returns:
            Formatted context lines
        """
        logger.debug("Getting context lines", line_number=line_number, context=context)
        start = max(0, line_number - context - 1)  # Convert to 0-indexed
        end = min(len(self.source_lines), line_number + context)

        context_lines = self.source_lines[start:end]
        return "\n".join(f"{i + start + 1:4d} | {line}" for i, line in enumerate(context_lines))

    # ====================
    # AST Utility Methods
    # ====================

    def get_source_segment(self, node: ast.AST) -> str:
        """
        Get source code for a specific AST node.

        Args:
            node: AST node

        Returns:
            Source code string for that node
        """
        logger.debug("Getting source segment for AST node", node_type=type(node).__name__)
        try:
            segment = ast.get_source_segment(self.source_code, node) or ""
            logger.debug("Source segment retrieved", length=len(segment))
            return segment
        except Exception as e:
            logger.debug("Failed to get source segment", error=str(e))
            return ""

    def is_name_match(
        self, node: ast.expr, name: str
    ) -> bool:  # noqa: CONST-V-001 - Simple AST utility
        """
        Check if AST expression node matches a name.

        Args:
            node: AST expression node
            name: Name to match (e.g., "os")

        Returns:
            True if node is a Name node with matching id
        """
        return isinstance(node, ast.Name) and node.id == name

    def is_attribute_call(self, node: ast.Call, object_name: str, attr_name: str) -> bool:
        """
        Check if Call node matches pattern: object_name.attr_name(...)

        Example: is_attribute_call(node, "os", "getenv")
        Matches: os.getenv("KEY")

        Args:
            node: Call AST node
            object_name: Object name (e.g., "os")
            attr_name: Attribute name (e.g., "getenv")

        Returns:
            True if matches pattern
        """
        logger.debug("Checking attribute call", object_name=object_name, attr_name=attr_name)
        if not isinstance(node.func, ast.Attribute):
            return False

        matches = (
            isinstance(node.func.value, ast.Name)
            and node.func.value.id == object_name
            and node.func.attr == attr_name
        )
        logger.debug("Attribute call check", matches=matches)
        return matches

    def find_decorator(
        self, node: ast.ClassDef | ast.FunctionDef, name: str
    ) -> bool:  # noqa: CONST-V-001 - Simple AST utility
        """
        Check if class/function has a specific decorator.

        Args:
            node: ClassDef or FunctionDef node
            name: Decorator name (e.g., "agent")

        Returns:
            True if decorator found
        """
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == name:
                return True
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                if decorator.func.id == name:
                    return True
        return False

    def has_base_class(self, node: ast.ClassDef, pattern: str) -> bool:
        """
        Check if class inherits from a base matching pattern.

        Args:
            node: ClassDef node
            pattern: String to search for in base class names

        Returns:
            True if any base class name contains pattern
        """
        logger.debug("Checking base class", class_name=node.name, pattern=pattern)
        for base in node.bases:
            if isinstance(base, ast.Name) and pattern in base.id:
                logger.debug("Base class match found", base=base.id)
                return True
            if isinstance(base, ast.Attribute) and pattern in base.attr:
                logger.debug("Base class match found", base=base.attr)
                return True
        logger.debug("No base class match", class_name=node.name)
        return False
