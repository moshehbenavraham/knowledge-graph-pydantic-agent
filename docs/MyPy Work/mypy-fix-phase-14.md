# MyPy Fix Phase 14: Type Annotations - constitution_validator/ + Misc

**Status**: Not Started
**Estimated Errors**: 15
**Files**: 6
**Prerequisites**: Phase 13 complete

---

## Objective

Add missing type annotations to `src/constitution_validator/` and remaining miscellaneous files.

---

## Files to Annotate

| File | Missing Annotations |
|------|---------------------|
| src/constitution_validator/models.py | 3 |
| src/constitution_validator/cli.py | 3 |
| src/constitution_validator/reporter.py | ~2 |
| src/constitution_validator/rules/base.py | ~2 |
| src/agent/unified_agent.py | ~3 |
| src/tools/*.py | ~2 |

---

## Constitution Validator Patterns

### Rule Classes
```python
# Before
class BaseRule:
    def __init__(self, name, description):
        self.name = name
        self.description = description

    def validate(self, context):
        ...

# After
from abc import ABC, abstractmethod

class BaseRule(ABC):
    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    @abstractmethod
    def validate(self, context: ValidationContext) -> ValidationResult:
        ...
```

### Validation Models
```python
# Before
class ValidationResult:
    def __init__(self, passed, violations, warnings):
        ...

# After
from dataclasses import dataclass

@dataclass
class ValidationResult:
    passed: bool
    violations: list[Violation]
    warnings: list[Warning]
    metadata: dict[str, Any]
```

### Reporter Functions
```python
# Before
def generate_report(results, format):
    ...

# After
from typing import Literal

ReportFormat = Literal["text", "json", "markdown", "html"]

def generate_report(
    results: list[ValidationResult],
    format: ReportFormat = "text"
) -> str:
    ...
```

---

## Agent/Tools Patterns

### Unified Agent
```python
# Before
async def run_agent(query, context):
    ...

# After
async def run_agent(
    query: str,
    context: AgentContext | None = None
) -> AgentResponse:
    ...
```

### Tool Functions
```python
# Before
async def retrieve_documents(ctx, query, k):
    ...

# After
from pydantic_ai import RunContext

async def retrieve_documents(
    ctx: RunContext[UnifiedAgentDeps],
    query: str,
    k: int = 10
) -> list[DocumentResult]:
    ...
```

---

## File-by-File Strategy

### constitution_validator/models.py (3 annotations)
- Pydantic models (should be mostly typed)
- Validation result types
- Error models

### constitution_validator/cli.py (3 annotations)
- Click command handlers
- File loading
- Output formatting

### constitution_validator/reporter.py (~2 annotations)
- Report generation
- Format conversion

### constitution_validator/rules/base.py (~2 annotations)
- Base rule class
- Abstract methods

### agent/unified_agent.py (~3 annotations)
- Agent factory
- Tool registration
- Context management

### tools/*.py (~2 annotations)
- Tool function signatures
- Already mostly typed via Pydantic AI

---

## Type Definitions to Add

```python
from typing import TypedDict
from dataclasses import dataclass
from enum import Enum

class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Violation:
    rule_name: str
    message: str
    severity: Severity
    location: str | None
    suggestion: str | None

@dataclass
class ValidationContext:
    file_path: str
    content: str
    metadata: dict[str, Any]

@dataclass
class AgentResponse:
    content: str
    tool_calls: list[dict[str, Any]]
    usage: TokenUsage
```

---

## Verification

```bash
# Check constitution_validator
mypy src/constitution_validator/ --ignore-missing-imports --disallow-untyped-defs

# Check agent and tools
mypy src/agent/ src/tools/ --ignore-missing-imports --disallow-untyped-defs
```

---

## Completion Checklist

- [ ] Annotate constitution_validator/models.py
- [ ] Annotate constitution_validator/cli.py
- [ ] Annotate constitution_validator/reporter.py
- [ ] Annotate constitution_validator/rules/base.py
- [ ] Annotate agent/unified_agent.py
- [ ] Review tools/*.py annotations
- [ ] Add shared type definitions
- [ ] Verify with mypy --disallow-untyped-defs
- [ ] Run test suite
- [ ] Commit changes

---

## Notes

- Click commands have decorator-based typing
- Pydantic AI tools should already have RunContext typed
- Constitution validator rules follow interface pattern
- Use Protocol for pluggable rule implementations
