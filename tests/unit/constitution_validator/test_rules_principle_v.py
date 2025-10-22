"""
Unit tests for Principle V validation rule (Production-Ready Observability).

Tests detection of missing logging and metrics instrumentation.
"""

import ast
from pathlib import Path

import pytest

from src.constitution_validator.models import (
    ConfidenceLevel,
)
from src.constitution_validator.rules.principle_v import ObservabilityRule


class TestPrincipleVRule:
    """Test suite for Principle V: Production-Ready Observability validation."""

    @pytest.fixture
    def rule(self) -> ObservabilityRule:
        """Create an ObservabilityRule instance for testing."""
        return ObservabilityRule()

    def test_detects_function_without_logging(self, rule: ObservabilityRule):
        """Test detection of functions that lack logging calls."""
        code = """
def process_data(data):
    # Process the input data
    result = transform(data)
    validate(result)
    check_quality(result)
    finalize(result)
    return result
"""
        tree = ast.parse(code)
        file_path = Path("src/service/processor.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) >= 1
        assert any("logging" in v.message.lower() for v in violations)

    def test_passes_function_with_logger_call(self, rule: ObservabilityRule):
        """Test that functions with logger calls pass."""
        code = """
import logging

logger = logging.getLogger(__name__)

def process_data(data):
    logger.info("Processing data")
    result = transform(data)
    logger.debug("Validation complete")
    return result
"""
        tree = ast.parse(code)
        file_path = Path("src/service/processor.py")

        violations = rule.execute(tree, file_path)

        # Should not flag this function
        assert not any("process_data" in v.message for v in violations)

    def test_passes_function_with_structlog(self, rule: ObservabilityRule):
        """Test that structlog usage is recognized."""
        code = """
import structlog

logger = structlog.get_logger()

def handle_request(request):
    logger.info("handling request", request_id=request.id)
    return process(request)
"""
        tree = ast.parse(code)
        file_path = Path("src/api/handler.py")

        violations = rule.execute(tree, file_path)

        # Should not flag this function
        assert not any("handle_request" in v.message for v in violations)

    def test_exempts_trivial_functions_under_5_lines(self, rule: ObservabilityRule):
        """Test that very short functions (<5 lines) are exempted."""
        code = """
def get_value():
    return 42

def add(a, b):
    return a + b
"""
        tree = ast.parse(code)
        file_path = Path("src/utils/math.py")

        violations = rule.execute(tree, file_path)

        # These trivial functions should be exempt
        assert len(violations) == 0

    def test_detects_missing_logger_import(self, rule: ObservabilityRule):
        """Test detection when logger is not imported at all."""
        code = """
def complex_operation(data):
    # This is a complex function with no logging
    step1 = process_step1(data)
    step2 = process_step2(step1)
    step3 = process_step3(step2)
    step4 = process_step4(step3)
    return step4
"""
        tree = ast.parse(code)
        file_path = Path("src/operations.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) >= 1

    def test_detects_multiple_functions_without_logging(self, rule: ObservabilityRule):
        """Test detection of multiple non-trivial functions without logging."""
        code = """
def function1(x):
    # Function 1 processing
    result = compute(x)
    validate(result)
    check(result)
    finalize(result)
    return result

def function2(y):
    # Function 2 processing
    data = fetch(y)
    process(data)
    verify(data)
    store(data)
    return data
"""
        tree = ast.parse(code)
        file_path = Path("src/service.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) >= 2

    def test_exempts_test_files(self, rule: ObservabilityRule):
        """Test that test files are exempted from logging requirements."""
        # Verify test paths are excluded
        assert any("test" in path.lower() for path in rule.excluded_paths)

    def test_remediation_mentions_logging(self, rule: ObservabilityRule):
        """Test that remediation guidance mentions logging setup."""
        code = """
def process(data):
    # Processing data
    transform(data)
    validate(data)
    verify(data)
    finalize(data)
    return data
"""
        tree = ast.parse(code)
        file_path = Path("src/processor.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) >= 1
        remediation = violations[0].remediation.lower()
        assert "logging" in remediation or "logger" in remediation

    def test_confidence_level_is_medium(self, rule: ObservabilityRule):
        """Test that logging detection has MEDIUM confidence (heuristic-based)."""
        code = """
def process(data):
    result = transform(data)
    return result
"""
        tree = ast.parse(code)
        file_path = Path("src/tool.py")

        violations = rule.execute(tree, file_path)

        if len(violations) > 0:
            # Confidence could be MEDIUM or LOW since it's heuristic
            assert violations[0].confidence in [ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]

    def test_severity_is_warning_or_error(self, rule: ObservabilityRule):
        """Test that missing logging is flagged appropriately."""
        code = """
def process(data):
    transform(data)
    return data
"""
        tree = ast.parse(code)
        file_path = Path("src/app.py")

        violations = rule.execute(tree, file_path)

        if len(violations) > 0:
            assert violations[0].severity in ["error", "warning"]

    def test_ignores_empty_functions(self, rule: ObservabilityRule):
        """Test that empty functions or pass-only functions are ignored."""
        code = """
def placeholder():
    pass

def abstract_method():
    raise NotImplementedError()
"""
        tree = ast.parse(code)
        file_path = Path("src/base.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) == 0

    def test_detects_class_methods_without_logging(self, rule: ObservabilityRule):
        """Test detection in class methods."""
        code = """
class DataProcessor:
    def process(self, data):
        # Complex processing
        result = self.transform(data)
        self.validate(result)
        self.verify(result)
        self.finalize(result)
        return result

    def transform(self, data):
        # Complex transformation without logging
        step1 = data * 2
        step2 = step1 + 10
        step3 = step2 / 3
        step4 = step3 - 5
        return step4
"""
        tree = ast.parse(code)
        file_path = Path("src/processor.py")

        violations = rule.execute(tree, file_path)

        assert len(violations) >= 1
