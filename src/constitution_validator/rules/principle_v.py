"""
Principle V validation rule: Production-Ready Observability.

Detects functions that lack logging instrumentation.
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


class ObservabilityRule(BaseValidationRule):
    """Validates adherence to Production-Ready Observability principle."""

    rule_id = "CONST-V-001"
    principle_id = "V"
    rule_name = "Detect missing logging instrumentation"

    MINIMUM_FUNCTION_LINES = 5  # Skip trivial functions

    # Configuration for test compatibility
    excluded_paths = ["tests/**"]
    included_paths = ["src/**/*.py"]

    def execute(
        self, tree: ast.AST, file_path: Path, source_code: str | None = None
    ) -> list[ViolationRecord]:
        """
        Execute validation on AST to detect missing logging.

        Args:
            tree: Parsed AST of the file
            file_path: Path to file being validated
            source_code: Optional source code (for tests or when file doesn't exist)

        Returns:
            List of violations detected
        """
        logger.info("Executing Principle V rule", rule_id=self.rule_id, file=str(file_path))
        # Prepare instance state
        self._prepare_execution(file_path, tree, source_code)

        # Skip test files
        if "test" in str(file_path):
            return []

        # Traverse AST looking for functions without logging
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip private functions, property getters, and trivial functions
                if self._should_skip_function(node):
                    continue

                # Check if function has logging calls
                if not self._has_logging(node):
                    self.add_violation(
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        message=f"Function '{node.name}' lacks logging instrumentation",
                        remediation=(
                            f"Add logging to function:\n"
                            f"  import structlog\n"
                            f"  logger = structlog.get_logger(__name__)\n"
                            f'  logger.info("Function {node.name} called", ...)'
                        ),
                        detected_code=f"def {node.name}",
                        suggested_fix="# Add logger.info/debug calls",
                        confidence=ConfidenceLevel.MEDIUM,
                        severity="warning",
                        metadata={"function_name": node.name, "line_count": len(node.body)},
                    )

        logger.info(
            "Principle V rule completed", rule_id=self.rule_id, violations=len(self.violations)
        )
        return self.violations

    def _should_skip_function(self, node: ast.FunctionDef) -> bool:
        """Check if function should be skipped from logging checks."""
        logger.debug("Checking if function should be skipped", function_name=node.name)
        # Skip private functions
        if node.name.startswith("_"):
            logger.debug("Skipping private function", function_name=node.name)
            return True

        # Skip property getters
        if self.find_decorator(node, "property"):
            return True

        # Skip Pydantic validators and model methods
        pydantic_patterns = [
            "validator",
            "field_validator",
            "model_validator",
            "root_validator",
        ]
        for pattern in pydantic_patterns:
            if self.find_decorator(node, pattern):
                return True

        # Skip Click command groups and commands with only pass/docstring
        # Check for @click.group(), @click.command(), @group, @command decorators
        has_click_decorator = False
        for decorator in node.decorator_list:
            # Handle @click.group() or @click.command()
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                if isinstance(decorator.func.value, ast.Name):
                    if decorator.func.value.id == "click" and decorator.func.attr in [
                        "group",
                        "command",
                    ]:
                        has_click_decorator = True
                        break
            # Handle @group or @command (simple decorators)
            if self.find_decorator(node, "group") or self.find_decorator(node, "command"):
                has_click_decorator = True
                break

        if has_click_decorator:
            # Check if function body is trivial (only pass statement + optional docstring)
            executable_stmts = [
                stmt
                for stmt in node.body
                if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Constant)
            ]
            if len(executable_stmts) == 1 and isinstance(executable_stmts[0], ast.Pass):
                logger.debug(
                    "Skipping Click decorator function with only pass", function_name=node.name
                )
                return True

        # Skip common utility/accessor patterns
        utility_patterns = [
            "to_dict",  # Serialization
            "to_json_dict",  # JSON serialization helper
            "from_dict",  # Deserialization
            "get_stats",  # Stats accessors
            "get_cache_stats",  # Cache stats accessors
            "get_config",  # Config accessors
            "dict",  # Dict conversion (Pydantic)
            "generate_key",  # Key generation utilities
            "compile_pathspec",  # Pathspec compilation utility
        ]
        if node.name in utility_patterns:
            return True

        # Skip validation methods (not decorators)
        if node.name.startswith("validate"):
            return True

        # Skip simple get/set accessors (cache, config)
        if node.name in ["get", "set"] and node.body:
            # Count actual executable statements (excluding docstring)
            executable_stmts = [
                stmt
                for stmt in node.body
                if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Constant)
            ]
            # Skip if few executable statements (likely simple accessor)
            if len(executable_stmts) <= 5:  # Simple accessors typically have <= 5 statements
                return True

        # Skip trivial functions (< 5 lines of code)
        # Calculate actual line span of function body
        if node.body:
            first_line = node.body[0].lineno
            last_line = node.body[-1].end_lineno or node.body[-1].lineno
            line_count = last_line - first_line + 1
            if line_count < self.MINIMUM_FUNCTION_LINES:
                return True

        return False

    def _has_logging(self, node: ast.FunctionDef) -> bool:
        """Check if function contains logging calls.

        Detects common logger patterns including:
        - Standard: logger, log
        - Structlog: structlog_logger, struct_logger, slog
        - Domain-specific: analytics_logger, audit_logger
        - Direct structlog calls: structlog.get_logger().info()
        """
        logger.debug("Checking for logging calls", function_name=node.name)

        # Extended list of recognized logger variable names
        logger_names = [
            "logger",
            "log",
            "structlog_logger",
            "struct_logger",
            "slog",
            "analytics_logger",
            "audit_logger",
        ]

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                # Pattern 1: logger.info() / structlog_logger.info()
                if isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name):
                        if child.func.value.id in logger_names:
                            logger.debug(
                                "Logging found via named logger",
                                function_name=node.name,
                                logger_var=child.func.value.id,
                            )
                            return True

                    # Pattern 2: structlog.get_logger().info()
                    if isinstance(child.func.value, ast.Call):
                        if isinstance(child.func.value.func, ast.Attribute):
                            if isinstance(child.func.value.func.value, ast.Name):
                                if child.func.value.func.value.id == "structlog":
                                    logger.debug(
                                        "Logging found via structlog.get_logger()",
                                        function_name=node.name,
                                    )
                                    return True

        logger.debug("No logging found", function_name=node.name)
        return False


# No alias needed - ObservabilityRule is the expected name
