"""
Principle II: Type-Safe Centralized Configuration

Detects direct os.getenv() and os.environ access violations.
"""

import ast
from pathlib import Path

import structlog

from ..models import ConfidenceLevel
from .base import BaseValidationRule

logger = structlog.get_logger(__name__)


class PrincipleIIRule(BaseValidationRule):
    """
    Validate Principle II: Type-Safe Centralized Configuration.

    Detects:
    - Direct os.getenv() calls
    - Direct os.environ[] access
    - os.environ.get() calls

    Exemptions:
    - src/config/settings.py (configuration module itself)
    - test files
    """

    RULE_ID = "CONST-II-001"
    PRINCIPLE_ID = "II"
    RULE_NAME = "Detect direct environment variable access"

    # Files exempt from this rule
    EXEMPT_FILES = {
        "src/config/settings.py",  # Configuration module can access env vars
        "src/config/__init__.py",
    }

    def __init__(self, file_path: Path, source_code: str):
        """Initialize Principle II rule."""
        super().__init__(
            file_path=file_path,
            source_code=source_code,
            rule_id=self.RULE_ID,
            principle_id=self.PRINCIPLE_ID,
            rule_name=self.RULE_NAME,
        )

    def execute(self) -> list:
        """
        Execute Principle II validation.

        Returns:
            List of violations detected
        """
        # Check if file is exempt
        file_str = str(self.file_path)
        if any(exempt in file_str for exempt in self.EXEMPT_FILES):
            logger.debug("File exempt from Principle II checks", file=file_str)
            return []

        # Run AST-based detection
        return self.check_ast()

    def visit_Call(self, node: ast.Call) -> None:
        """
        Visit Call nodes to detect os.getenv() and os.environ access.

        Patterns detected:
        1. os.getenv("VAR")
        2. os.getenv("VAR", "default")
        3. os.environ.get("VAR")
        4. os.environ["VAR"] (handled in visit_Subscript)
        """
        # Pattern 1 & 2: os.getenv(...)
        if self.is_attribute_call(node, "os", "getenv"):
            self._report_getenv_violation(node)

        # Pattern 3: os.environ.get(...)
        elif isinstance(node.func, ast.Attribute):
            # Check for os.environ.get()
            if (
                node.func.attr == "get"
                and isinstance(node.func.value, ast.Attribute)
                and isinstance(node.func.value.value, ast.Name)
                and node.func.value.value.id == "os"
                and node.func.value.attr == "environ"
            ):
                self._report_environ_get_violation(node)

        # Continue traversing
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """
        Visit Subscript nodes to detect os.environ["VAR"].

        Pattern: os.environ["KEY"]
        """
        # Check if subscript is os.environ[...]
        if isinstance(node.value, ast.Attribute):
            if (
                isinstance(node.value.value, ast.Name)
                and node.value.value.id == "os"
                and node.value.attr == "environ"
            ):
                self._report_environ_subscript_violation(node)

        # Continue traversing
        self.generic_visit(node)

    def _report_getenv_violation(self, node: ast.Call) -> None:
        """Report os.getenv() violation."""
        # Extract variable name from first argument
        var_name = "UNKNOWN"
        if node.args and isinstance(node.args[0], ast.Constant):
            var_name = node.args[0].value

        detected_code = self.get_source_segment(node)

        self.add_violation(
            line_number=node.lineno,
            column_number=node.col_offset,
            message=f"Direct os.getenv('{var_name}') usage detected",
            remediation=(
                f"Replace with centralized configuration:\n"
                f"  from src.config import get_settings\n"
                f"  settings = get_settings()\n"
                f"  {var_name.lower()} = settings.{var_name.lower()}\n\n"
                f"Or add '{var_name}' to src/config/settings.py if not present"
            ),
            detected_code=detected_code,
            suggested_fix=f"get_settings().{var_name.lower()}",
            confidence=ConfidenceLevel.HIGH,
            severity="error",
            metadata={"pattern": "os.getenv", "variable": var_name},
        )

    def _report_environ_get_violation(self, node: ast.Call) -> None:
        """Report os.environ.get() violation."""
        # Extract variable name from first argument
        var_name = "UNKNOWN"
        if node.args and isinstance(node.args[0], ast.Constant):
            var_name = node.args[0].value

        detected_code = self.get_source_segment(node)

        self.add_violation(
            line_number=node.lineno,
            column_number=node.col_offset,
            message=f"Direct os.environ.get('{var_name}') usage detected",
            remediation=(
                f"Replace with centralized configuration:\n"
                f"  from src.config import get_settings\n"
                f"  settings = get_settings()\n"
                f"  {var_name.lower()} = settings.{var_name.lower()}"
            ),
            detected_code=detected_code,
            suggested_fix=f"get_settings().{var_name.lower()}",
            confidence=ConfidenceLevel.HIGH,
            severity="error",
            metadata={"pattern": "os.environ.get", "variable": var_name},
        )

    def _report_environ_subscript_violation(self, node: ast.Subscript) -> None:
        """Report os.environ["VAR"] violation."""
        # Extract variable name from subscript
        var_name = "UNKNOWN"
        if isinstance(node.slice, ast.Constant):
            var_name = node.slice.value

        detected_code = self.get_source_segment(node)

        self.add_violation(
            line_number=node.lineno,
            column_number=node.col_offset,
            message=f"Direct os.environ['{var_name}'] access detected",
            remediation=(
                f"Replace with centralized configuration:\n"
                f"  from src.config import get_settings\n"
                f"  settings = get_settings()\n"
                f"  {var_name.lower()} = settings.{var_name.lower()}"
            ),
            detected_code=detected_code,
            suggested_fix=f"get_settings().{var_name.lower()}",
            confidence=ConfidenceLevel.HIGH,
            severity="error",
            metadata={"pattern": "os.environ[]", "variable": var_name},
        )
