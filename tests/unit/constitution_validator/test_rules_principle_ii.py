"""
Unit tests for Principle II validation rule (Centralized Configuration).

Tests detection of direct os.getenv() and os.environ[] access with exemptions.
"""

import ast
from pathlib import Path

import pytest

from src.constitution_validator.models import (
    ConfidenceLevel,
)
from src.constitution_validator.rules.principle_ii import CentralizedConfigRule


class TestPrincipleIIRule:
    """Test suite for Principle II: Centralized Configuration validation."""

    @pytest.fixture
    def rule(self) -> CentralizedConfigRule:
        """Create a CentralizedConfigRule instance for testing."""
        return CentralizedConfigRule()

    def test_detects_os_getenv_call(self, rule: CentralizedConfigRule):
        """Test detection of os.getenv() calls."""
        code = """
import os

api_key = os.getenv('API_KEY')
"""
        tree = ast.parse(code)
        file_path = Path("src/tools/example.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 1
        assert violations[0].rule_id == "CONST-II-001"
        assert violations[0].principle_id == "II"
        assert "os.getenv" in violations[0].message

    def test_detects_os_environ_subscript(self, rule: CentralizedConfigRule):
        """Test detection of os.environ[] access."""
        code = """
import os

database_url = os.environ['DATABASE_URL']
"""
        tree = ast.parse(code)
        file_path = Path("src/utils/db.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 1
        assert "os.environ" in violations[0].message

    def test_detects_os_environ_get(self, rule: CentralizedConfigRule):
        """Test detection of os.environ.get() calls."""
        code = """
import os

value = os.environ.get('MY_VAR', 'default')
"""
        tree = ast.parse(code)
        file_path = Path("src/service.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 1

    def test_detects_multiple_violations_in_file(self, rule: CentralizedConfigRule):
        """Test detection of multiple os.getenv calls in same file."""
        code = """
import os

api_key = os.getenv('API_KEY')
db_url = os.getenv('DB_URL')
secret = os.environ['SECRET']
"""
        tree = ast.parse(code)
        file_path = Path("src/config_violations.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 3

    def test_exempts_settings_file(self, rule: CentralizedConfigRule):
        """Test that src/config/settings.py is exempted."""
        # Exemption is path-based, verify it's in excluded_paths
        assert "src/config/settings.py" in rule.excluded_paths

    def test_inline_suppression_with_noqa(self, rule: CentralizedConfigRule):
        """Test that # noqa: CONST-II-001 suppresses violations."""
        code = """
import os

# This is suppressed
api_key = os.getenv('API_KEY')  # noqa: CONST-II-001 - Migration wrapper
"""
        tree = ast.parse(code)
        file_path = Path("src/legacy.py")

        violations = rule.execute(tree, file_path, source_code=code)

        # Should detect but mark as suppressed
        assert len(violations) == 1
        assert violations[0].suppressed is True
        assert "Migration wrapper" in violations[0].suppression_reason

    def test_inline_suppression_without_reason(self, rule: CentralizedConfigRule):
        """Test suppression without optional reason."""
        code = """
import os

api_key = os.getenv('API_KEY')  # noqa: CONST-II-001
"""
        tree = ast.parse(code)
        file_path = Path("src/code.py")

        violations = rule.execute(tree, file_path, source_code=code)

        assert len(violations) == 1
        assert violations[0].suppressed is True
        assert violations[0].suppression_reason is not None

    def test_ignores_other_function_calls(self, rule: CentralizedConfigRule):
        """Test that non-os.getenv calls are ignored."""
        code = """
import os

path = os.path.join('a', 'b')
exists = os.path.exists('/tmp')
value = my_custom_getenv('KEY')
"""
        tree = ast.parse(code)
        file_path = Path("src/utils.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 0

    def test_detects_with_default_value(self, rule: CentralizedConfigRule):
        """Test detection even when default value provided."""
        code = """
import os

port = os.getenv('PORT', '8000')
"""
        tree = ast.parse(code)
        file_path = Path("src/server.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 1

    def test_violation_includes_detected_code(self, rule: CentralizedConfigRule):
        """Test that violation includes the actual code snippet."""
        code = """
import os

api_key = os.getenv('API_KEY')
"""
        tree = ast.parse(code)
        file_path = Path("src/app.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 1
        assert violations[0].detected_code is not None
        assert "API_KEY" in violations[0].detected_code

    def test_remediation_mentions_get_settings(self, rule: CentralizedConfigRule):
        """Test that remediation guidance mentions get_settings()."""
        code = """
import os

value = os.getenv('VALUE')
"""
        tree = ast.parse(code)
        file_path = Path("src/tool.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 1
        assert "get_settings()" in violations[0].remediation
        assert "src/config/settings.py" in violations[0].remediation

    def test_confidence_level_is_high(self, rule: CentralizedConfigRule):
        """Test that AST-based detection has HIGH confidence."""
        code = """
import os

x = os.getenv('X')
"""
        tree = ast.parse(code)
        file_path = Path("src/file.py")

        violations = rule.execute(tree, file_path)

        assert violations[0].confidence == ConfidenceLevel.HIGH

    def test_severity_is_error(self, rule: CentralizedConfigRule):
        """Test that violations are errors."""
        code = """
import os

x = os.getenv('X')
"""
        tree = ast.parse(code)
        file_path = Path("src/file.py")

        violations = rule.execute(tree, file_path)

        assert violations[0].severity == "error"

    def test_empty_file(self, rule: CentralizedConfigRule):
        """Test handling of empty files."""
        code = ""
        tree = ast.parse(code)
        file_path = Path("src/empty.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 0
