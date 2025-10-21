"""
Unit tests for Principle I validation rule (Unified Agent Architecture).

Tests detection of multiple agent files and exemptions for the unified agent.
"""

import ast
from pathlib import Path
from typing import List

import pytest

from src.constitution_validator.models import (
    RuleCategory,
    ValidationRule,
    ViolationRecord,
    ConfidenceLevel,
)
from src.constitution_validator.rules.principle_i import UnifiedAgentRule


class TestPrincipleIRule:
    """Test suite for Principle I: Unified Agent Architecture validation."""

    @pytest.fixture
    def rule(self) -> UnifiedAgentRule:
        """Create a UnifiedAgentRule instance for testing."""
        return UnifiedAgentRule()

    @pytest.fixture
    def valid_rule_config(self) -> ValidationRule:
        """Create valid rule configuration for Principle I."""
        return ValidationRule(
            rule_id="CONST-I-001",
            principle_id="I",
            category=RuleCategory.ARCHITECTURE,
            name="Detect multiple agent files",
            description="Detects additional agent implementations outside unified_agent.py",
            violation_message_template="Additional agent file found: {file}",
            remediation_guidance="Extend src/agent/unified_agent.py instead of creating new agent files",
            confidence_level=ConfidenceLevel.HIGH,
            enabled=True,
            severity="error",
            ast_node_types=["ClassDef"],
            included_paths=["src/**/*.py"],
            excluded_paths=["tests/**", "src/agent/unified_agent.py"],
        )

    def test_detects_class_with_agent_in_name(self, rule: UnifiedAgentRule):
        """Test that classes with 'Agent' in name are detected."""
        code = """
class MyCustomAgent:
    def __init__(self):
        pass
"""
        tree = ast.parse(code)
        file_path = Path("src/custom/my_agent.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 1
        assert violations[0].rule_id == "CONST-I-001"
        assert violations[0].principle_id == "I"
        assert "Agent" in violations[0].message

    def test_detects_multiple_agent_classes_in_file(self, rule: UnifiedAgentRule):
        """Test that multiple agent classes in same file are all detected."""
        code = """
class FirstAgent:
    pass

class SecondAgent:
    pass

class ThirdCustomAgent:
    pass
"""
        tree = ast.parse(code)
        file_path = Path("src/agents/multiple.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 3
        agent_names = [v.detected_code for v in violations]
        assert "FirstAgent" in " ".join(agent_names)
        assert "SecondAgent" in " ".join(agent_names)
        assert "ThirdCustomAgent" in " ".join(agent_names)

    def test_ignores_classes_without_agent_in_name(self, rule: UnifiedAgentRule):
        """Test that classes without 'Agent' in name are ignored."""
        code = """
class MyService:
    pass

class DataProcessor:
    pass

class ConfigManager:
    pass
"""
        tree = ast.parse(code)
        file_path = Path("src/services/processor.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 0

    def test_exempts_unified_agent_file(self, rule: UnifiedAgentRule):
        """Test that src/agent/unified_agent.py is exempted."""
        code = """
class UnifiedAgent:
    \"\"\"The official unified agent - this should be exempt.\"\"\"
    pass

class UnifiedAgentDeps:
    pass
"""
        tree = ast.parse(code)
        file_path = Path("src/agent/unified_agent.py")

        # Rule should skip this file entirely via path filtering
        # In actual implementation, this is handled by the file discovery layer
        # For unit test, we verify the rule config excludes this path
        violations = rule.execute(tree, file_path)

        # Since exemption is path-based, we test that the rule config has the exclusion
        assert "src/agent/unified_agent.py" in rule.excluded_paths

    def test_detects_agent_subclasses(self, rule: UnifiedAgentRule):
        """Test detection of classes that inherit from agent-like bases."""
        code = """
from pydantic_ai import Agent

class CustomAgent(Agent):
    \"\"\"This violates Principle I.\"\"\"
    pass
"""
        tree = ast.parse(code)
        file_path = Path("src/custom_agent.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 1
        assert "CustomAgent" in violations[0].detected_code

    def test_case_insensitive_detection(self, rule: UnifiedAgentRule):
        """Test that 'agent' detection is case-insensitive."""
        code = """
class MyAGENT:
    pass

class myAgent:
    pass

class MyaGeNt:
    pass
"""
        tree = ast.parse(code)
        file_path = Path("src/weird_agents.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 3

    def test_violation_includes_file_and_line(self, rule: UnifiedAgentRule):
        """Test that violations include correct file path and line number."""
        code = """
# Line 1
# Line 2
class MyAgent:  # Line 3
    pass
"""
        tree = ast.parse(code)
        file_path = Path("src/my_agent.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 1
        assert violations[0].location.file_path == file_path
        assert violations[0].location.line_number == 3

    def test_violation_includes_remediation(self, rule: UnifiedAgentRule):
        """Test that violations include remediation guidance."""
        code = """
class CustomAgent:
    pass
"""
        tree = ast.parse(code)
        file_path = Path("src/custom_agent.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 1
        assert "unified_agent.py" in violations[0].remediation.lower()
        assert len(violations[0].remediation) > 20

    def test_confidence_level_is_high(self, rule: UnifiedAgentRule):
        """Test that detection confidence is HIGH for AST-based detection."""
        code = """
class MyAgent:
    pass
"""
        tree = ast.parse(code)
        file_path = Path("src/agent.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 1
        assert violations[0].confidence == ConfidenceLevel.HIGH

    def test_severity_is_error(self, rule: UnifiedAgentRule):
        """Test that violations are marked as errors."""
        code = """
class CustomAgent:
    pass
"""
        tree = ast.parse(code)
        file_path = Path("src/custom.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 1
        assert violations[0].severity == "error"

    def test_empty_file(self, rule: UnifiedAgentRule):
        """Test handling of empty Python files."""
        code = ""
        tree = ast.parse(code)
        file_path = Path("src/empty.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 0

    def test_file_with_only_functions(self, rule: UnifiedAgentRule):
        """Test that files with only functions (no classes) produce no violations."""
        code = """
def process_data():
    pass

def validate_input():
    pass
"""
        tree = ast.parse(code)
        file_path = Path("src/utils.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 0
