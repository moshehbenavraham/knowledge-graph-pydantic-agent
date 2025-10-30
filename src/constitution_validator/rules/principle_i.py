"""
Principle I validation rule: Unified Agent Architecture.

Detects additional agent implementations outside of src/agent/unified_agent.py.
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


class UnifiedAgentRule(BaseValidationRule):
    """Validates adherence to Unified Agent Architecture principle."""

    rule_id = "CONST-I-001"
    principle_id = "I"
    rule_name = "Detect multiple agent files"

    ALLOWED_AGENT_FILE = "src/agent/unified_agent.py"

    # Configuration for test compatibility
    excluded_paths = ["src/agent/unified_agent.py", "tests/**"]
    included_paths = ["src/**/*.py"]

    def execute(
        self, tree: ast.AST, file_path: Path, source_code: str | None = None
    ) -> list[ViolationRecord]:
        """
        Execute validation on AST to detect multiple agent files.

        Args:
            tree: Parsed AST of the file
            file_path: Path to file being validated
            source_code: Optional source code (for tests or when file doesn't exist)

        Returns:
            List of violations detected
        """
        logger.info("Executing Principle I rule", rule_id=self.rule_id, file=str(file_path))
        # Prepare instance state
        self._prepare_execution(file_path, tree, source_code)

        # Skip if this is the allowed agent file
        if str(file_path).endswith(self.ALLOWED_AGENT_FILE):
            return []

        # Traverse AST looking for agent-like classes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._is_agent_class(node):
                    self.add_violation(
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        message=f"Agent class '{node.name}' found outside unified_agent.py",
                        remediation=(
                            f"Move agent functionality to {self.ALLOWED_AGENT_FILE}.\n"
                            f"Use @super_agent.tool decorator for additional capabilities."
                        ),
                        detected_code=f"class {node.name}",
                        suggested_fix=f"# Move to {self.ALLOWED_AGENT_FILE}",
                        confidence=ConfidenceLevel.HIGH,
                        severity="error",
                        metadata={"class_name": node.name, "pattern": "agent_class"},
                    )

        logger.info(
            "Principle I rule completed", rule_id=self.rule_id, violations=len(self.violations)
        )
        return self.violations

    def _is_agent_class(self, node: ast.ClassDef) -> bool:
        """
        Check if class definition is an agent.

        Detection patterns:
        1. Class name ends with "Agent"
        2. Class has @agent decorator
        3. Class inherits from base class with "Agent" in name

        Args:
            node: ClassDef AST node

        Returns:
            True if class appears to be an agent
        """
        logger.debug("Checking if class is agent", class_name=node.name)

        # Pattern 1: @agent decorator
        if self.find_decorator(node, "agent"):
            logger.debug("Agent class detected via decorator", class_name=node.name)
            return True

        # Pattern 2: "Agent" suffix in class name (case-insensitive)
        if node.name.lower().endswith("agent"):
            logger.debug("Agent class detected via name suffix", class_name=node.name)
            return True

        # Pattern 3: Inherits from base agent class
        has_agent_base = bool(self.has_base_class(node, "Agent"))
        if has_agent_base:
            logger.debug("Agent class detected via base class", class_name=node.name)
        return has_agent_base


# Alias for test compatibility (already defined as UnifiedAgentRule)
