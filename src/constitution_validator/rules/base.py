"""
Base validation rule class with AST and regex utilities.

All principle-specific rules inherit from BaseValidationRule.
"""

import ast
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from ..models import ConfidenceLevel, ViolationLocation, ViolationRecord

logger = structlog.get_logger(__name__)


class BaseValidationRule(ABC, ast.NodeVisitor):
    """
    Base class for all constitutional validation rules.

    Provides:
    - AST traversal utilities
    - Regex matching utilities
    - Common violation detection patterns
    - Inline suppression support (# noqa: CONST-X-YYY)
    """

    def __init__(
        self,
        file_path: Path,
        source_code: str,
        rule_id: str,
        principle_id: str,
        rule_name: str,
    ):
        """
        Initialize base validation rule.

        Args:
            file_path: Path to file being validated
            source_code: Full source code of the file
            rule_id: Unique rule identifier (e.g., 'CONST-II-001')
            principle_id: Constitutional principle (I-VI)
            rule_name: Human-readable rule name
        """
        self.file_path = file_path
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.rule_id = rule_id
        self.principle_id = principle_id
        self.rule_name = rule_name
        self.violations: List[ViolationRecord] = []

        # Track current AST node for context
        self.current_node: Optional[ast.AST] = None

    @abstractmethod
    def execute(self) -> List[ViolationRecord]:
        """
        Execute validation rule and return violations.

        Subclasses MUST implement this method with their specific logic.

        Returns:
            List of detected violations
        """
        pass

    def check_ast(self) -> List[ViolationRecord]:
        """
        Parse file as AST and run visitor pattern.

        Returns:
            List of violations detected during AST traversal

        Handles:
            - Syntax errors in Python files
            - Parse failures
        """
        try:
            tree = ast.parse(self.source_code, filename=str(self.file_path))
            self.visit(tree)
            return self.violations
        except SyntaxError as e:
            logger.warning(
                "Syntax error in file, skipping AST checks",
                file=str(self.file_path),
                line=e.lineno,
                error=str(e),
            )
            # Don't report syntax errors as constitutional violations
            return []

    def add_violation(
        self,
        line_number: int,
        message: str,
        remediation: str,
        column_number: Optional[int] = None,
        detected_code: Optional[str] = None,
        suggested_fix: Optional[str] = None,
        confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
        severity: str = "error",
        metadata: Optional[Dict[str, Any]] = None,
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

    def _check_suppression(self, line_number: int) -> tuple[bool, Optional[str]]:
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
        if line_number < 1 or line_number > len(self.source_lines):
            return False, None

        line = self.source_lines[line_number - 1]  # Convert to 0-indexed

        # Check for # noqa: CONST-X-YYY or # noqa: CONSTITUTION-X
        noqa_pattern = r"#\s*noqa:\s*(CONST|CONSTITUTION)-([IVX]+)(?:-(\d+))?\s*(?:-\s*(.+))?"
        match = re.search(noqa_pattern, line, re.IGNORECASE)

        if not match:
            return False, None

        prefix, principle_id, rule_number, reason = match.groups()

        # Check if suppression applies to this rule
        if principle_id != self.principle_id:
            return False, None

        # If specific rule number given, check it matches
        if rule_number:
            expected_rule_id = f"CONST-{principle_id}-{rule_number}"
            if expected_rule_id != self.rule_id:
                return False, None

        return True, (reason.strip() if reason else "Suppressed via noqa comment")

    def _get_context_lines(self, line_number: int, context: int = 2) -> str:
        """
        Get surrounding lines for context.

        Args:
            line_number: Center line (1-indexed)
            context: Number of lines before/after

        Returns:
            Formatted context lines
        """
        start = max(0, line_number - context - 1)  # Convert to 0-indexed
        end = min(len(self.source_lines), line_number + context)

        context_lines = self.source_lines[start:end]
        return "\n".join(
            f"{i + start + 1:4d} | {line}" for i, line in enumerate(context_lines)
        )

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
        try:
            return ast.get_source_segment(self.source_code, node) or ""
        except Exception:
            return ""

    def is_name_match(self, node: ast.expr, name: str) -> bool:
        """
        Check if AST expression node matches a name.

        Args:
            node: AST expression node
            name: Name to match (e.g., "os")

        Returns:
            True if node is a Name node with matching id
        """
        return isinstance(node, ast.Name) and node.id == name

    def is_attribute_call(
        self, node: ast.Call, object_name: str, attr_name: str
    ) -> bool:
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
        if not isinstance(node.func, ast.Attribute):
            return False

        return (
            isinstance(node.func.value, ast.Name)
            and node.func.value.id == object_name
            and node.func.attr == attr_name
        )

    def find_decorator(self, node: ast.ClassDef | ast.FunctionDef, name: str) -> bool:
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
        for base in node.bases:
            if isinstance(base, ast.Name) and pattern in base.id:
                return True
            if isinstance(base, ast.Attribute) and pattern in base.attr:
                return True
        return False

    # ====================
    # Regex Utility Methods
    # ====================

    def find_regex_matches(
        self, pattern: str, flags: int = 0
    ) -> List[tuple[int, str]]:
        """
        Find all regex matches in source code.

        Args:
            pattern: Regex pattern
            flags: re module flags (e.g., re.IGNORECASE)

        Returns:
            List of (line_number, matched_text) tuples
        """
        matches = []
        for line_num, line in enumerate(self.source_lines, start=1):
            for match in re.finditer(pattern, line, flags):
                matches.append((line_num, match.group(0)))
        return matches

    def line_contains(self, line_number: int, substring: str) -> bool:
        """
        Check if a specific line contains substring.

        Args:
            line_number: Line to check (1-indexed)
            substring: Substring to search for

        Returns:
            True if substring found in line
        """
        if 1 <= line_number <= len(self.source_lines):
            return substring in self.source_lines[line_number - 1]
        return False
