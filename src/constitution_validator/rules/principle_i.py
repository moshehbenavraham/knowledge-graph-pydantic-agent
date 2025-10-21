"""
Principle I validation rule: Unified Agent Architecture.

Detects additional agent implementations outside of src/agent/unified_agent.py.
"""

import ast
from pathlib import Path
from typing import List

from src.constitution_validator.models import (
    ViolationRecord,
    ViolationLocation,
    ConfidenceLevel,
)
from src.constitution_validator.rules.base import ValidationRule


class UnifiedAgentRule(ValidationRule):
    """Validates adherence to Unified Agent Architecture principle."""

    def __init__(self):
        """Initialize the Unified Agent validation rule."""
        super().__init__(
            rule_id="CONST-I-001",
            principle_id="I",
            name="Detect multiple agent files",
            description="Detects additional agent implementations outside unified_agent.py",
            violation_message_template="Additional agent class found: {class_name} in {file}",
            remediation_guidance=(
                "Extend src/agent/unified_agent.py instead of creating new agent files. "
                "The Unified Agent Architecture principle requires ONE unified agent implementation. "
                "Add your functionality as tools or methods to the existing UnifiedAgent."
            ),
            confidence_level=ConfidenceLevel.HIGH,
            severity="error",
        )
        self.excluded_paths = [
            "tests/",
            "test_*.py",
            "*_test.py",
            "src/agent/unified_agent.py",  # The official unified agent is exempt
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

        # Walk the AST looking for class definitions with "Agent" in the name
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name

                # Check if "agent" appears in class name (case-insensitive)
                if "agent" in class_name.lower():
                    # Create violation record
                    violation = ViolationRecord(
                        rule_id=self.rule_id,
                        principle_id=self.principle_id,
                        location=ViolationLocation(
                            file_path=file_path,
                            line_number=node.lineno,
                            column_number=node.col_offset,
                        ),
                        message=self.violation_message_template.format(
                            class_name=class_name,
                            file=str(file_path)
                        ),
                        remediation=self.remediation_guidance,
                        confidence=self.confidence_level,
                        severity=self.severity,
                        detected_code=class_name,
                        suggested_fix=f"Add functionality to src/agent/unified_agent.py instead of {class_name}",
                    )

                    violations.append(violation)

        return violations
