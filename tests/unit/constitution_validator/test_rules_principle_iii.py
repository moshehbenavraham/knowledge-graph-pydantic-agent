"""
Unit tests for Principle III validation rule (Dual-Database Architecture).

Tests detection of direct database client instantiation.
"""

import ast
from pathlib import Path

import pytest

from src.constitution_validator.models import (
    ConfidenceLevel,
)
from src.constitution_validator.rules.principle_iii import DualDatabaseRule


class TestPrincipleIIIRule:
    """Test suite for Principle III: Dual-Database RAG validation."""

    @pytest.fixture
    def rule(self) -> DualDatabaseRule:
        """Create a DualDatabaseRule instance for testing."""
        return DualDatabaseRule()

    def test_detects_direct_supabase_client_instantiation(self, rule: DualDatabaseRule):
        """Test detection of direct Supabase client creation."""
        code = """
from supabase import create_client

client = create_client(url, key)
"""
        tree = ast.parse(code)
        file_path = Path("src/service/data.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) >= 1
        assert any("client" in v.message.lower() for v in violations)

    def test_detects_direct_neo4j_driver_instantiation(self, rule: DualDatabaseRule):
        """Test detection of direct Neo4j driver creation."""
        code = """
from neo4j import GraphDatabase

driver = GraphDatabase.driver(uri, auth=(user, password))
"""
        tree = ast.parse(code)
        file_path = Path("src/graph/service.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) >= 1
        assert any(
            "neo4j" in v.message.lower() or "driver" in v.message.lower() for v in violations
        )

    def test_exempts_clients_config_file(self, rule: DualDatabaseRule):
        """Test that src/config/clients.py is exempted."""
        code = """
from supabase import create_client

# This is the central client configuration - should be exempt
supabase_client = create_client(url, key)
"""
        _tree = ast.parse(code)
        _file_path = Path("src/config/clients.py")

        # Verify exemption is in excluded_paths
        assert "src/config/clients.py" in rule.excluded_paths

    def test_detects_postgresql_client_creation(self, rule: DualDatabaseRule):
        """Test detection of direct PostgreSQL client instantiation."""
        code = """
import psycopg2

conn = psycopg2.connect(host='localhost', database='db')
"""
        tree = ast.parse(code)
        file_path = Path("src/db/postgresql.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) >= 1

    def test_detects_multiple_client_instantiations(self, rule: DualDatabaseRule):
        """Test detection of multiple database clients in same file."""
        code = """
from supabase import create_client
from neo4j import GraphDatabase

supabase = create_client(url1, key1)
neo4j = GraphDatabase.driver(url2, auth2)
"""
        tree = ast.parse(code)
        file_path = Path("src/bad_practice.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) >= 2

    def test_ignores_safe_database_operations(self, rule: DualDatabaseRule):
        """Test that using existing clients doesn't trigger violations."""
        code = """
from src.config.clients import get_supabase_client, get_neo4j_driver

# Using centralized clients - this is correct
supabase = get_supabase_client()
neo4j = get_neo4j_driver()

# Queries are fine
result = supabase.table('users').select('*').execute()
"""
        tree = ast.parse(code)
        file_path = Path("src/service/user_service.py")

        violations = rule.execute(tree, file_path)

        # Should have no violations for using getter functions
        assert all("get_" not in v.detected_code for v in violations)

    def test_remediation_mentions_centralized_config(self, rule: DualDatabaseRule):
        """Test that remediation points to centralized client config."""
        code = """
from supabase import create_client

client = create_client(url, key)
"""
        tree = ast.parse(code)
        file_path = Path("src/tool.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) >= 1
        assert any("src/config/clients.py" in v.remediation for v in violations)

    def test_confidence_level(self, rule: DualDatabaseRule):
        """Test confidence level for detection."""
        code = """
from supabase import create_client

client = create_client(url, key)
"""
        tree = ast.parse(code)
        file_path = Path("src/app.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) >= 1
        assert violations[0].confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]

    def test_severity_is_error(self, rule: DualDatabaseRule):
        """Test that violations are marked as errors."""
        code = """
from neo4j import GraphDatabase

driver = GraphDatabase.driver(uri, auth)
"""
        tree = ast.parse(code)
        file_path = Path("src/test.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) >= 1
        assert violations[0].severity == "error"

    def test_empty_file(self, rule: DualDatabaseRule):
        """Test handling of empty files."""
        code = ""
        tree = ast.parse(code)
        file_path = Path("src/empty.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 0
