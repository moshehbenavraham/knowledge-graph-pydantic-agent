"""
Comprehensive tests for safe code execution tool.

Tests:
- Basic code execution
- Print output capture
- Allowed module imports
- Blocked module imports
- Built-in function availability
- Error handling
- Security restrictions
"""


from src.tools.code_execution import execute_safe_code_tool


class TestBasicCodeExecution:
    """Test basic code execution."""

    def test_simple_print(self):
        """Test simple print statement."""
        code = "print('Hello, World!')"
        result = execute_safe_code_tool(code)
        assert result == "Hello, World!\n"

    def test_multiple_prints(self):
        """Test multiple print statements."""
        code = """
print('Line 1')
print('Line 2')
print('Line 3')
"""
        result = execute_safe_code_tool(code)
        assert result == "Line 1\nLine 2\nLine 3\n"

    def test_print_with_separator(self):
        """Test print with custom separator."""
        code = "print('a', 'b', 'c', sep='-')"
        result = execute_safe_code_tool(code)
        assert result == "a-b-c\n"

    def test_print_with_end(self):
        """Test print with custom end."""
        code = """
print('Hello', end=' ')
print('World')
"""
        result = execute_safe_code_tool(code)
        assert result == "Hello World\n"

    def test_arithmetic_operations(self):
        """Test arithmetic operations."""
        code = """
result = 10 + 20 * 3 - 5
print(result)
"""
        result = execute_safe_code_tool(code)
        assert result == "65\n"

    def test_variable_assignment(self):
        """Test variable assignment and usage."""
        code = """
x = 42
y = x * 2
print(f"Result: {y}")
"""
        result = execute_safe_code_tool(code)
        assert result == "Result: 84\n"

    def test_string_operations(self):
        """Test string operations."""
        code = """
s = "hello"
print(s.upper())
print(s.capitalize())
print(len(s))
"""
        result = execute_safe_code_tool(code)
        assert result == "HELLO\nHello\n5\n"

    def test_list_operations(self):
        """Test list operations."""
        code = """
numbers = [1, 2, 3, 4, 5]
print(sum(numbers))
print(max(numbers))
print(sorted(numbers, reverse=True))
"""
        result = execute_safe_code_tool(code)
        assert "15\n" in result
        assert "5\n" in result
        assert "[5, 4, 3, 2, 1]" in result

    def test_dictionary_operations(self):
        """Test dictionary operations."""
        code = """
data = {"name": "Alice", "age": 30}
print(data["name"])
print(len(data))
"""
        result = execute_safe_code_tool(code)
        assert "Alice\n" in result
        assert "2\n" in result

    def test_function_definition(self):
        """Test function definition and calling."""
        code = """
def add(a, b):
    return a + b

result = add(10, 20)
print(result)
"""
        result = execute_safe_code_tool(code)
        assert result == "30\n"

    def test_loop_execution(self):
        """Test loop execution."""
        code = """
for i in range(3):
    print(f"Iteration {i}")
"""
        result = execute_safe_code_tool(code)
        assert "Iteration 0\n" in result
        assert "Iteration 1\n" in result
        assert "Iteration 2\n" in result

    def test_list_comprehension(self):
        """Test list comprehension."""
        code = """
squares = [x**2 for x in range(5)]
print(squares)
"""
        result = execute_safe_code_tool(code)
        assert "[0, 1, 4, 9, 16]" in result

    def test_conditional_logic(self):
        """Test conditional logic."""
        code = """
x = 10
if x > 5:
    print("Greater")
else:
    print("Lesser")
"""
        result = execute_safe_code_tool(code)
        assert result == "Greater\n"


class TestBuiltinFunctions:
    """Test available built-in functions."""

    def test_abs_function(self):
        """Test abs function."""
        code = "print(abs(-42))"
        result = execute_safe_code_tool(code)
        assert result == "42\n"

    def test_all_any_functions(self):
        """Test all and any functions."""
        code = """
print(all([True, True, True]))
print(any([False, False, True]))
"""
        result = execute_safe_code_tool(code)
        assert "True\n" in result

    def test_min_max_functions(self):
        """Test min and max functions."""
        code = """
numbers = [3, 1, 4, 1, 5, 9, 2]
print(min(numbers))
print(max(numbers))
"""
        result = execute_safe_code_tool(code)
        assert "1\n" in result
        assert "9\n" in result

    def test_sum_function(self):
        """Test sum function."""
        code = "print(sum([1, 2, 3, 4, 5]))"
        result = execute_safe_code_tool(code)
        assert result == "15\n"

    def test_sorted_function(self):
        """Test sorted function."""
        code = "print(sorted([3, 1, 4, 1, 5]))"
        result = execute_safe_code_tool(code)
        assert "[1, 1, 3, 4, 5]" in result

    def test_zip_function(self):
        """Test zip function."""
        code = """
a = [1, 2, 3]
b = ['a', 'b', 'c']
print(list(zip(a, b)))
"""
        result = execute_safe_code_tool(code)
        assert "(1, 'a')" in result

    def test_enumerate_function(self):
        """Test enumerate function."""
        code = """
for i, val in enumerate(['a', 'b', 'c']):
    print(f"{i}: {val}")
"""
        result = execute_safe_code_tool(code)
        assert "0: a\n" in result
        assert "1: b\n" in result

    def test_filter_function(self):
        """Test filter function."""
        code = """
numbers = [1, 2, 3, 4, 5]
evens = list(filter(lambda x: x % 2 == 0, numbers))
print(evens)
"""
        result = execute_safe_code_tool(code)
        assert "[2, 4]" in result

    def test_map_function(self):
        """Test map function."""
        code = """
numbers = [1, 2, 3]
squares = list(map(lambda x: x**2, numbers))
print(squares)
"""
        result = execute_safe_code_tool(code)
        assert "[1, 4, 9]" in result


class TestAllowedModules:
    """Test allowed module imports."""

    def test_import_datetime(self):
        """Test importing datetime module."""
        code = """
import datetime
now = datetime.datetime.now()
print(type(now).__name__)
"""
        result = execute_safe_code_tool(code)
        assert "datetime" in result

    def test_import_math(self):
        """Test importing math module."""
        code = """
import math
print(math.pi)
print(math.sqrt(16))
"""
        result = execute_safe_code_tool(code)
        assert "3.14" in result
        assert "4.0" in result

    def test_import_random(self):
        """Test importing random module."""
        code = """
import random
random.seed(42)
print(random.randint(1, 10))
"""
        result = execute_safe_code_tool(code)
        # Should execute without error
        assert len(result) > 0

    def test_import_json(self):
        """Test importing json module."""
        code = """
import json
data = {"name": "Alice", "age": 30}
json_str = json.dumps(data)
print(json_str)
"""
        result = execute_safe_code_tool(code)
        assert '"name"' in result
        assert '"age"' in result

    def test_import_re(self):
        """Test importing re module."""
        code = """
import re
pattern = r"\\d+"
text = "There are 42 apples"
match = re.search(pattern, text)
print(match.group())
"""
        result = execute_safe_code_tool(code)
        assert "42" in result

    def test_import_collections(self):
        """Test importing collections module."""
        code = """
import collections
counter = collections.Counter(['a', 'b', 'a', 'c', 'b', 'a'])
print(counter['a'])
"""
        result = execute_safe_code_tool(code)
        assert "3" in result

    def test_import_itertools(self):
        """Test importing itertools module."""
        code = """
import itertools
combos = list(itertools.combinations([1, 2, 3], 2))
print(len(combos))
"""
        result = execute_safe_code_tool(code)
        assert "3" in result

    def test_import_statistics(self):
        """Test importing statistics module."""
        code = """
import statistics
data = [1, 2, 3, 4, 5]
print(statistics.mean(data))
"""
        result = execute_safe_code_tool(code)
        assert "3" in result

    def test_import_uuid(self):
        """Test importing uuid module."""
        code = """
import uuid
uid = uuid.uuid4()
print(type(uid).__name__)
"""
        result = execute_safe_code_tool(code)
        assert "UUID" in result


class TestBlockedModules:
    """Test blocked module imports."""

    def test_import_os_blocked(self):
        """Test os module is blocked."""
        code = "import os"
        result = execute_safe_code_tool(code)
        assert "Error executing code:" in result
        assert "os" in result

    def test_import_sys_blocked(self):
        """Test sys module is blocked."""
        code = "import sys"
        result = execute_safe_code_tool(code)
        assert "Error executing code:" in result

    def test_import_subprocess_blocked(self):
        """Test subprocess module is blocked."""
        code = "import subprocess"
        result = execute_safe_code_tool(code)
        assert "Error executing code:" in result

    def test_import_socket_blocked(self):
        """Test socket module is blocked."""
        code = "import socket"
        result = execute_safe_code_tool(code)
        assert "Error executing code:" in result

    def test_import_requests_blocked(self):
        """Test requests module is blocked."""
        code = "import requests"
        result = execute_safe_code_tool(code)
        assert "Error executing code:" in result


class TestErrorHandling:
    """Test error handling."""

    def test_syntax_error(self):
        """Test handling syntax error."""
        code = "print('unclosed string"
        result = execute_safe_code_tool(code)
        assert "Error executing code:" in result

    def test_name_error(self):
        """Test handling name error."""
        code = "print(undefined_variable)"
        result = execute_safe_code_tool(code)
        assert "Error executing code:" in result
        assert "undefined_variable" in result

    def test_type_error(self):
        """Test handling type error."""
        code = "result = '10' + 10"
        result = execute_safe_code_tool(code)
        assert "Error executing code:" in result

    def test_zero_division_error(self):
        """Test handling zero division error."""
        code = "result = 10 / 0"
        result = execute_safe_code_tool(code)
        assert "Error executing code:" in result
        assert "division" in result.lower()

    def test_index_error(self):
        """Test handling index error."""
        code = """
numbers = [1, 2, 3]
print(numbers[10])
"""
        result = execute_safe_code_tool(code)
        assert "Error executing code:" in result

    def test_key_error(self):
        """Test handling key error."""
        code = """
data = {"a": 1}
print(data["b"])
"""
        result = execute_safe_code_tool(code)
        assert "Error executing code:" in result


class TestSecurityRestrictions:
    """Test security restrictions."""

    def test_file_operations_restricted(self):
        """Test file operations are restricted (no open)."""
        code = "with open('/etc/passwd', 'r') as f: print(f.read())"
        result = execute_safe_code_tool(code)
        assert "Error executing code:" in result

    def test_eval_not_available(self):
        """Test eval is not available."""
        code = "result = eval('1 + 1')"
        result = execute_safe_code_tool(code)
        assert "Error executing code:" in result

    def test_exec_within_code_blocked(self):
        """Test nested exec is not available."""
        code = "exec('print(\"nested\")')"
        result = execute_safe_code_tool(code)
        assert "Error executing code:" in result

    def test_compile_not_available(self):
        """Test compile is not available."""
        code = "code_obj = compile('print(1)', '<string>', 'exec')"
        result = execute_safe_code_tool(code)
        assert "Error executing code:" in result


class TestComplexScenarios:
    """Test complex code scenarios."""

    def test_class_definition(self):
        """Test class definition and instantiation."""
        code = """
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def distance(self):
        import math
        return math.sqrt(self.x**2 + self.y**2)

p = Point(3, 4)
print(p.distance())
"""
        result = execute_safe_code_tool(code)
        assert "5.0" in result

    def test_nested_functions(self):
        """Test nested function definitions."""
        code = """
def outer(x):
    def inner(y):
        return x + y
    return inner(10)

print(outer(5))
"""
        result = execute_safe_code_tool(code)
        assert "15" in result

    def test_exception_handling(self):
        """Test exception handling within code."""
        code = """
try:
    result = 10 / 0
except ZeroDivisionError:
    print("Caught division by zero")
"""
        result = execute_safe_code_tool(code)
        assert "Caught division by zero" in result

    def test_data_processing(self):
        """Test data processing scenario."""
        code = """
data = [
    {"name": "Alice", "score": 85},
    {"name": "Bob", "score": 92},
    {"name": "Charlie", "score": 78}
]

total = sum(item["score"] for item in data)
average = total / len(data)
print(f"Average score: {average:.2f}")
"""
        result = execute_safe_code_tool(code)
        assert "Average score: 85.00" in result

    def test_json_processing(self):
        """Test JSON processing."""
        code = """
import json

json_str = '{"users": [{"name": "Alice"}, {"name": "Bob"}]}'
data = json.loads(json_str)
print(len(data["users"]))
"""
        result = execute_safe_code_tool(code)
        assert "2" in result
