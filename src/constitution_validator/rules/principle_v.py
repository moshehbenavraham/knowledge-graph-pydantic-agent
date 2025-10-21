"""
Principle V validation rule: Production-Ready Observability.

Detects functions that lack logging instrumentation.
"""

import ast
from pathlib import Path
from typing import List, Set

from src.constitution_validator.models import (
    ViolationRecord,
    ViolationLocation,
    ConfidenceLevel,
)
from src.constitution_validator.rules.base import ValidationRule


class ObservabilityRule(ValidationRule):
    """Validates adherence to Production-Ready Observability principle."""

    def __init__(self):
        """Initialize the Observability validation rule."""
        super().__init__(
            rule_id="CONST-V-001",
            principle_id="V",
            name="Detect missing logging instrumentation",
            description="Detects functions without proper logging calls",
            violation_message_template="Function '{function}' lacks logging instrumentation in {file}",
            remediation_guidance=(
                "Add logging to this function using structlog or Python's logging module. "
                "Import: from structlog import get_logger; logger = get_logger() "
                "Then add logger.info/debug/error calls at key points in the function."
            ),
            confidence_level=ConfidenceLevel.MEDIUM,  # Heuristic-based
            severity="warning",  # Less critical than architecture violations
        )
        self.excluded_paths = [
            "tests/",
            "test_*.py",
            "*_test.py",
        ]

    def execute(self, tree: ast.AST, file_path: Path) -> List[ViolationRecord]:
        """
        Execute the rule on an AST tree.

        Args:
            tree: Parsed AST of the Python file
            file_path: Path to the file being validated

        Returns:
            List of violation records found
        """
        violations = []

        # Check if file has logging imports
        has_logging_import = self._check_logging_imports(tree)

        # Find all function definitions
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip trivial functions (< 5 lines)
                if self._is_trivial_function(node):
                    continue

                # Check if function has logging calls
                has_logging_calls = self._has_logging_calls(node)

                # If no logging import or no logging calls, report violation
                if not has_logging_import or not has_logging_calls:
                    violation = ViolationRecord(
                        rule_id=self.rule_id,
                        principle_id=self.principle_id,
                        location=ViolationLocation(
                            file_path=file_path,
                            line_number=node.lineno,
                            column_number=node.col_offset,
                        ),
                        message=self.violation_message_template.format(
                            function=node.name,
                            file=str(file_path)
                        ),
                        remediation=self.remediation_guidance,
                        confidence=self.confidence_level,
                        severity=self.severity,
                        detected_code=node.name,
                        suggested_fix=f"Add logger.info() calls in {node.name}()",
                    )

                    violations.append(violation)

        return violations

    def _check_logging_imports(self, tree: ast.AST) -> bool:
        """Check if file imports logging or structlog."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "logging" in alias.name or "structlog" in alias.name:
                        return True
            elif isinstance(node, ast.ImportFrom):
                if node.module and ("logging" in node.module or "structlog" in node.module):
                    return True
        return False

    def _has_logging_calls(self, func_node: ast.FunctionDef) -> bool:
        """Check if function contains logging calls."""
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                call_str = self._get_call_string(node)
                # Check for common logging patterns
                if any(pattern in call_str.lower() for pattern in [
                    "logger.", "log.", ".info(", ".debug(", ".error(", ".warning("
                ]):
                    return True
        return False

    def _is_trivial_function(self, func_node: ast.FunctionDef) -> bool:
        """
        Check if function is trivial (< 5 lines or just pass/return/raise).

        Args:
            func_node: Function AST node

        Returns:
            True if function is trivial and exempt from logging requirement
        """
        # Count non-trivial statements
        non_trivial_statements = 0
        for node in func_node.body:
            if isinstance(node, (ast.Pass, ast.Return)):
                # These are trivial
                if isinstance(node, ast.Return) and node.value is None:
                    continue
            if isinstance(node, ast.Expr):
                # Docstrings are trivial
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    continue
            non_trivial_statements += 1

        return non_trivial_statements < 3

    def _get_call_string(self, node: ast.Call) -> str:
        """Extract string representation of a call."""
        try:
            if isinstance(node.func, ast.Attribute):
                return f"{self._get_name(node.func.value)}.{node.func.attr}"
            elif isinstance(node.func, ast.Name):
                return node.func.id
            return ""
        except Exception:
            return ""

    def _get_name(self, node: ast.AST) -> str:
        """Extract name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""
