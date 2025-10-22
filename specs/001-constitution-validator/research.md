# Research: Python AST Parsing for Constitution Validator

**Feature**: Constitution Compliance Validator
**Date**: 2025-10-21
**Research Focus**: Static code analysis patterns for detecting constitutional violations

## Executive Summary

**Decision**: Use Python's standard library `ast` module with custom `NodeVisitor` subclasses for all code analysis.

**Rationale**:
- **Performance**: Built in C, parses 50k LOC codebases in ~8 seconds (acceptable for <30s requirement)
- **Zero dependencies**: Stdlib only, works in air-gapped environments
- **Sufficient for analysis-only**: Lossy AST is fine since we don't need to preserve formatting
- **Battle-tested**: Powers PyLint, Flake8, and most Python linters
- **Simple patterns**: Constitutional violations involve straightforward syntax detection (function calls, class names, missing decorators)

**Rejected Alternatives**:
- **libcst**: Slower parsing (~3x overhead), preserves whitespace (unnecessary for validation), requires Python 3.9+
- **astroid**: Additional dependency, type inference overkill for our use case (we need syntax detection, not type analysis)

**Expected Performance**: 10-50k LOC codebase validation in 15-25 seconds (AST parsing 8s + rule execution 7-17s)

---

## Detection Strategies

### 1. Detect `os.getenv()` Calls (Principle II Violations)

**Pattern**: Attribute call where `func` is `ast.Attribute` with `value.id == "os"` and `attr == "getenv"`

**AST Structure**:
```python
# Code: os.getenv("API_KEY")
ast.Call(
    func=ast.Attribute(
        value=ast.Name(id='os'),
        attr='getenv'
    ),
    args=[ast.Constant(value='API_KEY')]
)
```

**Visitor Implementation**:
```python
class ConfigViolationDetector(ast.NodeVisitor):
    """Detects direct os.getenv() usage (Principle II violation)."""

    def __init__(self):
        self.violations = []

    def visit_Call(self, node: ast.Call) -> None:
        """Check if call is os.getenv() or os.environ access."""
        # Pattern 1: os.getenv("VAR")
        if isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and
                node.func.value.id == "os" and
                node.func.attr in ("getenv", "environ")):
                self.violations.append({
                    "file": self.current_file,
                    "line": node.lineno,
                    "col": node.col_offset,
                    "type": "direct_os_getenv",
                    "principle": "II",
                    "message": "Direct os.getenv() usage detected",
                    "remediation": "Use get_settings() from src/config/settings.py"
                })

        # Continue traversing child nodes
        self.generic_visit(node)
```

**False Positive Handling**:
- **Test files**: Legitimate os.getenv() usage in test fixtures
  - **Solution**: Skip files matching `tests/`, `test_*.py`, `*_test.py` patterns
- **Vendored code**: Third-party libraries in `vendor/` or `.venv/`
  - **Solution**: Use `.constitution-ignore` file (gitignore-style patterns)
- **Migration code**: Temporary compatibility wrappers
  - **Solution**: Allow `# noqa: CONSTITUTION-II` inline comments

---

### 2. Detect Multiple Agent Files (Principle I Violations)

**Pattern**: Classes decorated with `@agent` or containing "Agent" in name (excluding test agents, base classes)

**AST Structure**:
```python
# Code: @agent class MyAgent: pass
ast.ClassDef(
    name='MyAgent',
    decorator_list=[ast.Name(id='agent')],
    bases=[]
)
```

**Visitor Implementation**:
```python
class AgentArchitectureDetector(ast.NodeVisitor):
    """Detects multiple agent implementations (Principle I violation)."""

    ALLOWED_AGENT_FILE = "src/agent/unified_agent.py"

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check for agent-like classes outside unified_agent.py."""
        # Skip if we're in the allowed agent file
        if self.file_path.endswith(self.ALLOWED_AGENT_FILE):
            self.generic_visit(node)
            return

        # Pattern 1: @agent decorator
        has_agent_decorator = any(
            isinstance(dec, ast.Name) and dec.id == "agent"
            for dec in node.decorator_list
        )

        # Pattern 2: "Agent" suffix in class name
        has_agent_suffix = node.name.endswith("Agent")

        # Pattern 3: Inherits from base agent classes
        inherits_agent = any(
            isinstance(base, ast.Name) and "Agent" in base.id
            for base in node.bases
        )

        if has_agent_decorator or (has_agent_suffix and inherits_agent):
            self.violations.append({
                "file": self.file_path,
                "line": node.lineno,
                "class_name": node.name,
                "type": "multiple_agents",
                "principle": "I",
                "message": f"Agent class '{node.name}' found outside unified_agent.py",
                "remediation": "Move functionality to src/agent/unified_agent.py as @super_agent.tool"
            })

        self.generic_visit(node)
```

**False Positive Handling**:
- **Test agents**: Mock agents in test files
  - **Solution**: Exclude `tests/` directory entirely
- **Base classes**: `BaseAgent` abstract classes
  - **Solution**: Check for `abc.ABC` inheritance or `@abstractmethod` decorators
- **External libraries**: Imported agent frameworks
  - **Solution**: Only scan `src/` directory

---

### 3. Detect Direct Database Client Instantiation (Principle III Violations)

**Pattern**: Direct construction of `SupabaseClient`, `Neo4jDriver`, `AsyncDriver` (should use `ConnectionManager`)

**AST Structure**:
```python
# Code: client = SupabaseClient(url, key)
ast.Assign(
    targets=[ast.Name(id='client')],
    value=ast.Call(
        func=ast.Name(id='SupabaseClient'),
        args=[...]
    )
)
```

**Visitor Implementation**:
```python
class DatabaseClientDetector(ast.NodeVisitor):
    """Detects direct database client instantiation (Principle III violation)."""

    PROHIBITED_CLIENTS = {
        "SupabaseClient", "Neo4jDriver", "AsyncDriver",
        "GraphDatabase", "PostgresConnection"
    }

    ALLOWED_FILES = {
        "src/agentic_rag/storage/connection_manager.py",
        "tests/"  # Tests can instantiate for mocking
    }

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations = []

    def visit_Call(self, node: ast.Call) -> None:
        """Check for direct instantiation of database clients."""
        # Skip allowed files
        if any(self.file_path.startswith(allowed) for allowed in self.ALLOWED_FILES):
            self.generic_visit(node)
            return

        # Check if calling a prohibited client constructor
        if isinstance(node.func, ast.Name):
            if node.func.id in self.PROHIBITED_CLIENTS:
                self.violations.append({
                    "file": self.file_path,
                    "line": node.lineno,
                    "client": node.func.id,
                    "type": "direct_db_client",
                    "principle": "III",
                    "message": f"Direct instantiation of {node.func.id} detected",
                    "remediation": "Use ConnectionManager from src/agentic_rag/storage/connection_manager.py"
                })

        self.generic_visit(node)
```

**False Positive Handling**:
- **Connection manager itself**: Needs to instantiate clients
  - **Solution**: Whitelist `src/agentic_rag/storage/connection_manager.py`
- **Test fixtures**: Need real client instances for integration tests
  - **Solution**: Allow in `tests/integration/` but flag in `tests/unit/`
- **Type hints**: `client: SupabaseClient` is usage, not instantiation
  - **Solution**: Only check `ast.Call` nodes, not `ast.AnnAssign`

---

### 4. Detect Missing Logging/Metrics (Principle V Violations)

**Pattern**: Function definitions without `logger` calls or `analytics_logger` usage

**AST Structure**:
```python
# Compliant code:
def my_function():
    logger.info("Starting operation")  # Has logger call
    # ...

# Violation:
def my_function():
    # No logger call in body
    pass
```

**Visitor Implementation**:
```python
class ObservabilityDetector(ast.NodeVisitor):
    """Detects missing logging/metrics in new feature code (Principle V)."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations = []
        self.current_function = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check if function has logging/metrics calls."""
        # Skip private helpers, tests, and simple getters
        if (node.name.startswith("_") or
            self.file_path.startswith("tests/") or
            self._is_simple_getter(node)):
            self.generic_visit(node)
            return

        # Check function body for logger/metrics usage
        has_logger = self._has_logger_call(node)
        has_metrics = self._has_metrics_call(node)

        # Flag public functions in src/ without observability
        if (not has_logger and not has_metrics and
            self.file_path.startswith("src/") and
            len(node.body) > 2):  # Non-trivial function

            self.violations.append({
                "file": self.file_path,
                "line": node.lineno,
                "function": node.name,
                "type": "missing_observability",
                "principle": "V",
                "message": f"Function '{node.name}' lacks logging/metrics",
                "remediation": "Add logger.info/debug calls or analytics events"
            })

        self.generic_visit(node)

    def _has_logger_call(self, node: ast.FunctionDef) -> bool:
        """Check if function body contains logger.* calls."""
        for child in ast.walk(node):
            if (isinstance(child, ast.Call) and
                isinstance(child.func, ast.Attribute) and
                isinstance(child.func.value, ast.Name) and
                child.func.value.id in ("logger", "analytics_logger")):
                return True
        return False

    def _has_metrics_call(self, node: ast.FunctionDef) -> bool:
        """Check for metrics/analytics event logging."""
        for child in ast.walk(node):
            if (isinstance(child, ast.Call) and
                isinstance(child.func, ast.Attribute) and
                child.func.attr in ("log_search", "log_tool_usage")):
                return True
        return False

    def _is_simple_getter(self, node: ast.FunctionDef) -> bool:
        """Check if function is a simple getter/property."""
        return (len(node.body) == 1 and
                isinstance(node.body[0], ast.Return))
```

**False Positive Handling**:
- **Simple getters**: `def get_name(self): return self.name`
  - **Solution**: Skip functions with single `return` statement
- **Private helpers**: `def _internal_helper()` (should use parent's logger)
  - **Solution**: Skip functions starting with `_`
- **Test code**: Tests don't need production logging
  - **Solution**: Exclude `tests/` directory
- **Short functions**: One-liners or trivial logic
  - **Solution**: Only flag functions with >2 statements

---

## Performance Optimization Strategies

### 1. Incremental Validation (Pre-commit Mode)
```python
def get_changed_files() -> List[str]:
    """Get files modified in git staging area (pre-commit)."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True, text=True
    )
    return [f for f in result.stdout.split('\n') if f.endswith('.py')]
```
**Impact**: Reduces validation from 50k LOC → ~500 LOC (100x speedup for typical commit)

### 2. Parallel File Processing
```python
from concurrent.futures import ProcessPoolExecutor

def validate_codebase(files: List[str]) -> List[Violation]:
    """Validate files in parallel using process pool."""
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = executor.map(validate_file, files)
    return list(itertools.chain.from_iterable(results))
```
**Impact**: 4-core system validates 4x faster (25s → 6s for full codebase)

### 3. AST Caching
```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1024)
def parse_file_cached(file_path: str, file_hash: str) -> ast.AST:
    """Cache parsed AST by file content hash."""
    with open(file_path) as f:
        return ast.parse(f.read(), filename=file_path)
```
**Impact**: Repeat validations (CI reruns) use cached ASTs (8s → <1s parsing)

### 4. Early Exit on Critical Violations
```python
def validate_with_fail_fast(files: List[str], max_violations: int = 10) -> Report:
    """Stop validation after finding critical violation threshold."""
    violations = []
    for file in files:
        violations.extend(validate_file(file))
        if len(violations) >= max_violations:
            break  # Stop early, developer needs to fix these first
    return Report(violations=violations, truncated=len(violations) >= max_violations)
```
**Impact**: Stops at 10 violations instead of scanning entire codebase (variable speedup)

---

## Benchmark Estimates

**Test Environment**: Python 3.11, 4-core CPU, SSD

| Codebase Size | Full Validation | Pre-commit (Incremental) | Cached Re-run |
|---------------|-----------------|--------------------------|---------------|
| 10k LOC (50 files) | 5s | 0.5s | 0.2s |
| 50k LOC (250 files) | 18s | 1.2s | 0.8s |
| 100k LOC (500 files) | 28s | 2.5s | 1.5s |

**Breakdown** (50k LOC):
- AST parsing: 8s (44%)
- Rule execution: 7s (39%)
- Report generation: 2s (11%)
- File I/O: 1s (6%)

**Meets Performance Goals**:
- ✅ Full validation <30s (18s for 50k LOC)
- ✅ Pre-commit <5s (1.2s for typical commit)

---

## False Positive Reduction

### 1. Path-Based Exclusions
```python
# .constitution-ignore (gitignore syntax via pathspec library)
tests/
*.generated.py
vendor/
.venv/
migrations/alembic/versions/*.py
```

### 2. Inline Suppressions
```python
# Allow with explanation comment
db_client = Neo4jDriver(uri, auth)  # noqa: CONSTITUTION-III - migration compatibility
```

### 3. Context-Aware Checks
```python
def is_test_file(file_path: str) -> bool:
    """Check if file is a test (multiple signals)."""
    return (
        file_path.startswith("tests/") or
        file_path.endswith("_test.py") or
        "test_" in os.path.basename(file_path) or
        _contains_test_fixtures(file_path)  # Parse for @pytest.fixture
    )
```

### 4. Rule Confidence Levels
```python
class ViolationRecord(BaseModel):
    confidence: Literal["high", "medium", "low"]

# High confidence: Direct os.getenv() call in src/
# Medium confidence: Class named "CustomAgent" (could be domain model)
# Low confidence: Function without logger (might be trivial)
```

**Expected False Positive Rate**: <5% based on confidence filtering

---

## Library Comparison Details

### Python `ast` (Chosen)
**Pros**:
- Standard library (no dependencies)
- Fast C implementation
- Sufficient for syntax detection
- Battle-tested (powers all major linters)

**Cons**:
- Lossy (no whitespace/comments)
- No type inference

**Use Cases**: Read-only analysis, linting, validation

---

### `libcst` (Rejected)
**Pros**:
- Preserves exact source (lossless CST)
- Can reconstruct original code
- Good for code transformations

**Cons**:
- 3x slower parsing than ast
- Unnecessary complexity for validation
- Requires Python 3.9+

**Use Cases**: Code formatters, refactoring tools, automated code modification

---

### `astroid` (Rejected)
**Pros**:
- Type inference capabilities
- Powers Pylint
- Advanced static analysis

**Cons**:
- Additional dependency
- Overkill for syntax detection
- Slower than ast

**Use Cases**: Advanced linting with type checking, unused import detection

---

## Code Examples: Complete Visitor Pattern

### Base Visitor Class
```python
from typing import List, Dict, Any
import ast

class BaseConstitutionRule(ast.NodeVisitor):
    """Base class for all constitution validation rules."""

    def __init__(self, file_path: str, source_code: str):
        self.file_path = file_path
        self.source_code = source_code
        self.violations: List[Dict[str, Any]] = []

    def check(self) -> List[Dict[str, Any]]:
        """Parse and check file, return violations."""
        try:
            tree = ast.parse(self.source_code, filename=self.file_path)
            self.visit(tree)
            return self.violations
        except SyntaxError as e:
            return [{
                "file": self.file_path,
                "line": e.lineno,
                "type": "parse_error",
                "message": f"Syntax error: {e.msg}",
                "principle": None
            }]
```

### Example Rule Usage
```python
def validate_file(file_path: str) -> List[Dict[str, Any]]:
    """Run all constitutional rules on a file."""
    with open(file_path) as f:
        source = f.read()

    rules = [
        ConfigViolationDetector(file_path, source),
        AgentArchitectureDetector(file_path, source),
        DatabaseClientDetector(file_path, source),
        ObservabilityDetector(file_path, source),
    ]

    violations = []
    for rule in rules:
        violations.extend(rule.check())

    return violations
```

---

## Implementation Recommendations

1. **Start with `ast.NodeVisitor`** - Sufficient for all detection needs
2. **Use process pool** - Parallelize file validation (4 workers)
3. **Implement incremental mode** - Git diff for pre-commit speed
4. **Add confidence levels** - Filter low-confidence violations by default
5. **Comprehensive ignore patterns** - `.constitution-ignore` + inline `# noqa`
6. **Cache parsed ASTs** - Hash-based caching for CI reruns
7. **Fail-fast mode** - Stop at 10 violations for quick feedback
8. **Context-aware checks** - Detect test files via multiple signals

---

## Git Commit Message Analysis

### Decision: GitPython with Regex Pattern Matching

**Chosen approach**: Use GitPython for commit iteration and trailer parsing, combined with regex for message body validation.

**Rationale**:
- **Structured API** - Clean Python objects with built-in trailer parsing (`commit.trailers_dict`)
- **Maintainability** - More readable than subprocess string parsing
- **Performance** - Adequate for 100-1000 commits (validates in <1 second)
- **Built-in support** - `commit.co_authors` and auto-parsed trailers

**Alternatives rejected**:
- `subprocess (git log)`: More brittle, harder to test
- `dulwich`: Pure Python but slower, less convenient API

### Implementation Pattern

```python
from git import Repo
import re

def validate_commit_attribution(repo_path: str, commit_sha: str) -> dict:
    """Validate commit for prohibited AI attribution patterns."""
    repo = Repo(repo_path)
    commit = repo.commit(commit_sha)

    violations = []

    # Check trailers for Co-Authored-By: Claude
    trailers = commit.trailers_dict
    co_authors = trailers.get('Co-authored-by', [])

    for author in co_authors:
        if re.search(r'claude|anthropic', author, re.IGNORECASE):
            violations.append(f"co-author-prohibited: {author}")

    # Check message body for attribution text
    prohibited_patterns = [
        r'Generated with.*Claude Code',
        r'Co-Authored-By:.*Claude',
        r'\bAnthropic\b',
        r'\bClaude\b.*\bnoreply@anthropic\.com\b'
    ]

    for pattern in prohibited_patterns:
        if re.search(pattern, commit.message, re.IGNORECASE):
            violations.append(f"message-attribution: {pattern}")

    return {
        "has_violations": len(violations) > 0,
        "violations": violations,
        "commit_summary": commit.summary[:50]
    }
```

### Scope: Unpushed Commits Only (`origin/main..HEAD`)

**Reasoning**:
- **Actionable** - Users can amend unpushed commits
- **Performance** - Typically 1-20 commits (validates in <1s)
- **Practical** - Pushed commits are immutable on protected branches

**CLI flags for alternative scopes**:
- `--all-local`: All commits on current branch
- `--since <date>`: Commits since timestamp
- `--last-n <count>`: Last N commits only

### Edge Cases

- **Merge commits** - Multiple co-authors are legitimate
- **Amended commits** - Re-validate on different SHA
- **Empty messages** - Handle with clear error
- **Non-ASCII** - Regex handles emoji (`🤖`)

**Dependency**: Add `GitPython>=3.1.45` to `pyproject.toml`

---

## pytest-cov Integration

### Decision: coverage.py API (Read .coverage file)

**Chosen approach**: Read existing `.coverage` SQLite database using coverage.py API, don't re-run tests.

**Rationale**:
- **Performance** - Reading .coverage takes ~50ms vs 30-60s for running tests
- **Separation of concerns** - Validator checks compliance, users run tests separately
- **Reliability** - coverage.py is the underlying library for pytest-cov
- **Simplicity** - Single method call returns coverage percentage

**Alternatives rejected**:
- `pytest.main()`: Complex, requires running full test suite (slow)
- `subprocess + pytest`: Reliable but overkill for reading results
- `JSON report parsing`: More detailed but slower

### Implementation Pattern

```python
from coverage import Coverage
import io

def validate_coverage(min_coverage: float = 75.0) -> tuple[bool, float, str]:
    """Read .coverage SQLite file and validate against minimum."""
    try:
        cov = Coverage(data_file=".coverage")
        cov.load()

        output = io.StringIO()
        total_coverage = cov.report(file=output, show_missing=False)

        passed = total_coverage >= min_coverage
        message = f"{'✓' if passed else '✗'} Coverage {total_coverage:.1f}% (min: {min_coverage}%)"

        return (passed, total_coverage, message)

    except Exception as e:
        return (False, 0.0, f"Error reading coverage: {e}")
```

### Limitations

1. **Must run tests first** - .coverage file must exist
2. **Stale data risk** - Coverage can be outdated if code changed
3. **New files invisible** - Files not in database return `None`
4. **Dependency requirement** - coverage package must be installed

**Error handling**:
- Missing .coverage → "No .coverage file found - run 'make test-coverage' first"
- Import error → "coverage package not installed"
- Corrupted file → "Delete .coverage and re-run tests"

**Performance**: Read .coverage (50ms) << Run tests (30s)

---

## Click CLI Best Practices

### Pattern: Dual Output Modes (JSON default, text optional)

```python
import click
import json

@click.command()
@click.option('--format', type=click.Choice(['json', 'text']), default='json')
@click.option('--verbose', is_flag=True, help='Show all checks, not just violations')
@click.argument('paths', nargs=-1, type=click.Path(exists=True))
def validate(format, verbose, paths):
    """Validate code against constitutional principles."""
    result = run_validation(paths or ['.'], verbose=verbose)

    if format == 'json':
        click.echo(json.dumps(result, indent=2))
    else:
        print_human_readable(result)

    sys.exit(0 if result['passed'] else 1)
```

---

## Pre-commit Hook Integration

### Pattern: Local Hook Entry Point

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: constitution-validator
        name: Constitution Compliance
        entry: constitution-validate
        language: python
        pass_filenames: true
        types: [python]
        stages: [commit]
```

Validator receives changed files as arguments, scans only those files.

---

## Pattern Matching for .constitution-ignore

### Decision: pathspec Library

```python
import pathspec

def load_ignore_patterns(ignore_file: str = ".constitution-ignore") -> pathspec.PathSpec:
    """Load ignore patterns from .constitution-ignore file."""
    if not os.path.exists(ignore_file):
        return pathspec.PathSpec.from_lines('gitwildmatch', [])

    with open(ignore_file) as f:
        patterns = f.read().splitlines()

    return pathspec.PathSpec.from_lines('gitwildmatch', patterns)
```

**Default patterns**:
```
tests/
.venv/
venv/
__pycache__/
*.pyc
.git/
vendor/
```

---

## Summary of Dependencies

**Required packages** (add to `pyproject.toml`):
- `click>=8.1.0` - CLI framework
- `GitPython>=3.1.45` - Git commit analysis
- `coverage>=7.0.0` - Coverage validation
- `pathspec>=0.11.0` - .gitignore pattern matching

**Stdlib modules**:
- `ast` - Code parsing
- `json` - Output formatting
- `re` - Pattern matching
- `multiprocessing` - Parallel scanning

---

## Performance Summary

| Operation | Target | Expected |
|-----------|--------|----------|
| Full codebase scan (50k LOC) | <30s | ~18s |
| Pre-commit (5 files) | <5s | ~1s |
| Coverage check | <1s | ~50ms |
| Git commit validation (20 commits) | <2s | ~500ms |

**Overall**: Meets all performance requirements.

---

## References

- [Python AST Documentation](https://docs.python.org/3/library/ast.html)
- [Learn Python ASTs by Building Your Own Linter (DeepSource)](https://deepsource.com/blog/python-asts-by-building-your-own-linter)
- [LibCST: Why Not AST?](https://libcst.readthedocs.io/en/latest/why_libcst.html)
- [Analyzing Python Code with Python (Rotem Tamir)](https://rotemtam.com/2020/08/13/python-ast/)
- [Python AST Performance Issues (GitHub CodeQL #6964)](https://github.com/github/codeql/issues/6964)
- [GitPython Documentation](https://gitpython.readthedocs.io/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
