"""
Principle III validation rule: Dual-Database Architecture.

Detects direct database client instantiation instead of using centralized configuration.
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


class DualDatabaseRule(ValidationRule):
    """Validates adherence to Dual-Database RAG principle."""

    def __init__(self):
        """Initialize the Dual-Database validation rule."""
        super().__init__(
            rule_id="CONST-III-001",
            principle_id="III",
            name="Detect direct database client instantiation",
            description="Detects direct creation of database clients instead of using centralized configuration",
            violation_message_template="Direct database client instantiation found: {call} in {file}",
            remediation_guidance=(
                "Use centralized database clients from src/config/clients.py instead. "
                "Import get_supabase_client() or get_neo4j_driver() rather than creating clients directly. "
                "This ensures consistent configuration and connection pooling."
            ),
            confidence_level=ConfidenceLevel.HIGH,
            severity="error",
        )
        self.excluded_paths = [
            "tests/",
            "test_*.py",
            "*_test.py",
            "src/config/clients.py",  # Central client config is exempt
        ]

        # Patterns to detect
        self.client_patterns = [
            "create_client",  # Supabase
            "GraphDatabase.driver",  # Neo4j
            "psycopg2.connect",  # PostgreSQL direct
            "Neo4jDriver",  # Direct Neo4j driver
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

        # Walk the AST looking for function calls that create database clients
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_string = self._get_call_string(node)

                # Check if this matches any of our client creation patterns
                for pattern in self.client_patterns:
                    if pattern.lower() in call_string.lower():
                        violation = ViolationRecord(
                            rule_id=self.rule_id,
                            principle_id=self.principle_id,
                            location=ViolationLocation(
                                file_path=file_path,
                                line_number=node.lineno,
                                column_number=node.col_offset,
                            ),
                            message=self.violation_message_template.format(
                                call=call_string,
                                file=str(file_path)
                            ),
                            remediation=self.remediation_guidance,
                            confidence=self.confidence_level,
                            severity=self.severity,
                            detected_code=call_string,
                            suggested_fix="Use get_supabase_client() or get_neo4j_driver() from src/config/clients.py",
                        )

                        violations.append(violation)
                        break  # Only report once per call

        return violations

    def _get_call_string(self, node: ast.Call) -> str:
        """
        Extract a string representation of a function call.

        Args:
            node: AST Call node

        Returns:
            String representation of the call
        """
        try:
            if isinstance(node.func, ast.Name):
                return node.func.id
            elif isinstance(node.func, ast.Attribute):
                # Handle chained attributes like GraphDatabase.driver
                parts = []
                current = node.func
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.append(current.id)
                return ".".join(reversed(parts))
            else:
                return ""
        except Exception:
            return ""
