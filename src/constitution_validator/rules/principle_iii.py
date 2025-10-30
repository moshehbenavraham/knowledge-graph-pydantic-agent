"""
Principle III validation rule: Dual-Database Architecture.

Detects direct database client instantiation instead of using centralized configuration.
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


class DualDatabaseRule(BaseValidationRule):
    """Validates adherence to Dual-Database RAG principle."""

    rule_id = "CONST-III-001"
    principle_id = "III"
    rule_name = "Detect direct database client instantiation"

    PROHIBITED_CLIENTS = [
        "SupabaseClient",
        "Neo4jDriver",
        "AsyncDriver",
        "GraphDatabase",
        "PostgresConnection",
        "Client",  # Supabase client
        "create_client",  # Supabase factory function
        "create_async_driver",  # Neo4j async factory
        "AsyncClient",  # PostgreSQL async client
        "psycopg2",  # PostgreSQL client library
        "connect",  # Database connection method
    ]

    EXEMPTED_FILES = [
        "src/config/clients.py",
        "src/agentic_rag/storage/connection_manager.py",
    ]

    # Configuration for test compatibility
    excluded_paths = [
        "src/config/clients.py",
        "src/agentic_rag/storage/connection_manager.py",
        "tests/**",
    ]
    included_paths = ["src/**/*.py"]

    def execute(
        self, tree: ast.AST, file_path: Path, source_code: str | None = None
    ) -> list[ViolationRecord]:
        """
        Execute validation on AST to detect direct database client instantiation.

        Args:
            tree: Parsed AST of the file
            file_path: Path to file being validated
            source_code: Optional source code (for tests or when file doesn't exist)

        Returns:
            List of violations detected
        """
        logger.info("Executing Principle III rule", rule_id=self.rule_id, file=str(file_path))
        # Prepare instance state
        self._prepare_execution(file_path, tree, source_code)

        # Skip exempted files
        if any(str(file_path).endswith(exempt) for exempt in self.EXEMPTED_FILES):
            return []

        # Traverse AST looking for direct client instantiation
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                client_name = self._get_client_name(node)
                if client_name in self.PROHIBITED_CLIENTS:
                    self.add_violation(
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        message=f"Direct instantiation of {client_name} detected",
                        remediation=(
                            "Use centralized configuration instead:\n"
                            "  from src.config import get_settings\n"
                            "  settings = get_settings()\n"
                            "  # Use configured clients from src/config/clients.py via ConnectionManager"
                        ),
                        detected_code=self.get_source_segment(node),
                        suggested_fix="# Use ConnectionManager.get_client()",
                        confidence=ConfidenceLevel.HIGH,
                        severity="error",
                        metadata={"pattern": "direct_client_instantiation", "client": client_name},
                    )

                # Also check for class method patterns like GraphDatabase.driver()
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        class_name = node.func.value.id
                        method_name = node.func.attr
                        # Check if calling prohibited class methods
                        if class_name in self.PROHIBITED_CLIENTS or method_name in [
                            "driver",
                            "connect",
                        ]:
                            if class_name in self.PROHIBITED_CLIENTS:
                                self.add_violation(
                                    line_number=node.lineno,
                                    column_number=node.col_offset,
                                    message=f"Direct {class_name}.{method_name}() call detected",
                                    remediation=(
                                        "Use centralized configuration instead:\n"
                                        "  from src.agentic_rag.storage.connection_manager import ConnectionManager\n"
                                        "  # Get client from ConnectionManager"
                                    ),
                                    detected_code=self.get_source_segment(node),
                                    suggested_fix="# Use ConnectionManager",
                                    confidence=ConfidenceLevel.HIGH,
                                    severity="error",
                                    metadata={
                                        "pattern": "class_method_call",
                                        "class": class_name,
                                        "method": method_name,
                                    },
                                )

        logger.info(
            "Principle III rule completed", rule_id=self.rule_id, violations=len(self.violations)
        )
        return self.violations

    def _get_client_name(self, node: ast.Call) -> str:
        """Extract client class name from Call node."""
        logger.debug("Extracting client name from call node")
        if isinstance(node.func, ast.Name):
            client_name = node.func.id
            logger.debug("Client name extracted from Name", client_name=client_name)
            return client_name
        if isinstance(node.func, ast.Attribute):
            client_name = node.func.attr
            logger.debug("Client name extracted from Attribute", client_name=client_name)
            return client_name
        logger.debug("No client name found")
        return ""


# No alias needed - DualDatabaseRule is the expected name
