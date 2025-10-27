"""
Principle V validation rule: Production-Ready Observability.

Detects functions that lack logging instrumentation.
"""

import ast
from pathlib import Path

from src.constitution_validator.models import (
    ConfidenceLevel,
    ViolationRecord,
)
from src.constitution_validator.rules.base import BaseValidationRule


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

        return self.violations

    def _should_skip_function(self, node: ast.FunctionDef) -> bool:
        """Check if function should be skipped from logging checks."""
        # Skip private functions
        if node.name.startswith("_"):
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

        # Skip common utility/accessor patterns
        utility_patterns = [
            "to_dict",  # Serialization
            "from_dict",  # Deserialization
            "get_stats",  # Stats accessors
            "get_config",  # Config accessors
            "dict",  # Dict conversion (Pydantic)
            "generate_key",  # Key generation utilities
        ]
        if node.name in utility_patterns:
            return True

        # Skip validation methods (not decorators)
        if node.name.startswith("validate"):
            return True

        # Skip simple get/set accessors (cache, config)
        if node.name in ["get", "set"] and node.body:
            # Only skip if very short (likely cache accessor)
            first_line = node.body[0].lineno
            last_line = node.body[-1].end_lineno or node.body[-1].lineno
            line_count = last_line - first_line + 1
            if line_count < 8:  # Simple accessors are typically < 8 lines
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
        """Check if function contains logging calls."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                # Check for logger.info/debug/warning/error calls
                if isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name):
                        if child.func.value.id in ["logger", "analytics_logger", "log"]:
                            return True
        return False


# No alias needed - ObservabilityRule is the expected name
