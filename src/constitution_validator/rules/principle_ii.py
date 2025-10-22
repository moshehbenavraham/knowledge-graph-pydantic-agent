"""
Principle II validation rule: Centralized Configuration.

Detects direct os.getenv() usage instead of centralized configuration.
"""

import ast
from pathlib import Path

from src.constitution_validator.models import (
    ConfidenceLevel,
    ViolationRecord,
)
from src.constitution_validator.rules.base import BaseValidationRule


class PrincipleIIRule(BaseValidationRule):
    """Validates adherence to Centralized Configuration principle."""

    rule_id = "CONST-II-001"
    principle_id = "II"
    rule_name = "Detect direct os.getenv() usage"

    EXEMPTED_FILES = ["src/config/settings.py"]

    # Configuration for test compatibility
    excluded_paths = ["src/config/settings.py", "tests/**"]
    included_paths = ["src/**/*.py"]

    def execute(
        self, tree: ast.AST, file_path: Path, source_code: str | None = None
    ) -> list[ViolationRecord]:
        """
        Execute validation on AST to detect direct environment variable access.

        Args:
            tree: Parsed AST of the file
            file_path: Path to file being validated
            source_code: Optional source code (for tests or when file doesn't exist)

        Returns:
            List of violations detected
        """
        # Prepare instance state
        self._prepare_execution(file_path, tree, source_code)

        # Skip exempted files
        if any(str(file_path).endswith(exempt) for exempt in self.EXEMPTED_FILES):
            return []

        # Traverse AST looking for os.getenv() or os.environ access
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Pattern 1: os.getenv("KEY")
                if self.is_attribute_call(node, "os", "getenv"):
                    var_name = self._extract_var_name_from_call(node)
                    self.add_violation(
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        message=f"Direct os.getenv('{var_name}') call detected",
                        remediation=(
                            f"Use centralized configuration instead:\n"
                            f"  from src.config import get_settings\n"
                            f"  settings = get_settings()\n"
                            f"  value = settings.{var_name.lower()}"
                        ),
                        detected_code=self.get_source_segment(node),
                        suggested_fix=f"get_settings().{var_name.lower()}",
                        confidence=ConfidenceLevel.HIGH,
                        severity="error",
                        metadata={"pattern": "os.getenv", "variable": var_name},
                    )

                # Pattern 2: os.environ.get("KEY")
                elif isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                    if isinstance(node.func.value, ast.Attribute):
                        if (
                            isinstance(node.func.value.value, ast.Name)
                            and node.func.value.value.id == "os"
                            and node.func.value.attr == "environ"
                        ):
                            var_name = self._extract_var_name_from_call(node)
                            self.add_violation(
                                line_number=node.lineno,
                                column_number=node.col_offset,
                                message=f"Direct os.environ.get('{var_name}') call detected",
                                remediation=(
                                    f"Use centralized configuration instead:\n"
                                    f"  from src.config import get_settings\n"
                                    f"  settings = get_settings()\n"
                                    f"  value = settings.{var_name.lower()}"
                                ),
                                detected_code=self.get_source_segment(node),
                                suggested_fix=f"get_settings().{var_name.lower()}",
                                confidence=ConfidenceLevel.HIGH,
                                severity="error",
                                metadata={"pattern": "os.environ.get", "variable": var_name},
                            )

            elif isinstance(node, ast.Subscript):
                # Pattern: os.environ["KEY"]
                # Structure: Subscript(value=Attribute(value=Name(id='os'), attr='environ'), slice=...)
                if isinstance(node.value, ast.Attribute):
                    if isinstance(node.value.value, ast.Name) and node.value.value.id == "os":
                        if node.value.attr == "environ":
                            var_name = self._extract_var_name_from_subscript(node)
                            self.add_violation(
                                line_number=node.lineno,
                                column_number=node.col_offset,
                                message=f"Direct os.environ['{var_name}'] access detected",
                                remediation=(
                                    f"Use centralized configuration instead:\n"
                                    f"  from src.config import get_settings\n"
                                    f"  settings = get_settings()\n"
                                    f"  value = settings.{var_name.lower()}"
                                ),
                                detected_code=self.get_source_segment(node),
                                suggested_fix=f"get_settings().{var_name.lower()}",
                                confidence=ConfidenceLevel.HIGH,
                                severity="error",
                                metadata={"pattern": "os.environ[]", "variable": var_name},
                            )

        return self.violations

    def _extract_var_name_from_call(self, node: ast.Call) -> str:
        """Extract variable name from os.getenv(var_name) call."""
        if node.args and isinstance(node.args[0], ast.Constant):
            return node.args[0].value
        return "UNKNOWN"

    def _extract_var_name_from_subscript(self, node: ast.Subscript) -> str:
        """Extract variable name from os.environ[var_name] subscript."""
        if isinstance(node.slice, ast.Constant):
            return node.slice.value
        return "UNKNOWN"


# Alias for test compatibility
CentralizedConfigRule = PrincipleIIRule
