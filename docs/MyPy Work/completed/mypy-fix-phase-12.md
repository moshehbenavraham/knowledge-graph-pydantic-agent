# MyPy Fix Phase 12: Type Annotations - ui/ Module

**Status**: COMPLETED
**Estimated Errors**: 25
**Files**: 6
**Prerequisites**: Phase 11 complete
**Completed**: 2025-11-27

---

## Objective

Add missing type annotations to the `src/ui/` module (Streamlit UI and feature handlers).

---

## Files to Annotate

| File | Missing Annotations |
|------|---------------------|
| src/ui/streamlit_app.py | 9 |
| src/ui/features/base_handler.py | 6 |
| src/ui/features/upload_handler.py | 4 |
| src/ui/features/memory_handler.py | 4 |
| src/ui/features/streaming_handler.py | ~2 |
| src/ui/features/mcp_handler.py | ~2 |

---

## Streamlit-Specific Patterns

### Handler Classes
```python
# Before
class BaseHandler:
    def __init__(self, config):
        self.config = config

    async def handle_message(self, message):
        ...

# After
from typing import Any

class BaseHandler:
    def __init__(self, config: HandlerConfig) -> None:
        self.config = config

    async def handle_message(self, message: str) -> ChatResponse:
        ...
```

### Session State Access
```python
# Before
def get_session_value(key, default):
    return st.session_state.get(key, default)

# After
from typing import TypeVar

T = TypeVar('T')

def get_session_value(key: str, default: T) -> T:
    return st.session_state.get(key, default)
```

### File Upload Handling
```python
# Before
def process_upload(uploaded_file):
    ...

# After
from streamlit.runtime.uploaded_file_manager import UploadedFile

def process_upload(uploaded_file: UploadedFile) -> ProcessedFile:
    ...
```

### Streaming Responses
```python
# Before
async def stream_response(response_generator):
    ...

# After
from collections.abc import AsyncGenerator

async def stream_response(
    response_generator: AsyncGenerator[str, None]
) -> str:
    ...
```

---

## File-by-File Strategy

### streamlit_app.py (9 annotations)
- App initialization
- Page rendering
- Session management
- Navigation handling

### features/base_handler.py (6 annotations)
- Base handler class
- Common utilities
- Message formatting
- Error handling

### features/upload_handler.py (4 annotations)
- File upload processing
- Document extraction
- Image handling
- Tabular data parsing

### features/memory_handler.py (4 annotations)
- Mem0 integration
- Memory retrieval
- Context building
- Memory storage

### features/streaming_handler.py (~2 annotations)
- Stream processing
- Chunk handling
- Tool call display

### features/mcp_handler.py (~2 annotations)
- MCP server integration
- Context injection
- Server management

---

## Type Definitions to Add

```python
from typing import TypedDict, Protocol
from dataclasses import dataclass
from enum import Enum

class UIMode(Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    ADVANCED = "advanced"

@dataclass
class HandlerConfig:
    mode: UIMode
    enable_streaming: bool
    enable_memory: bool
    enable_mcp: bool

@dataclass
class ChatResponse:
    content: str
    tool_calls: list[ToolCall]
    metadata: dict[str, Any]

class ProcessedFile(TypedDict):
    name: str
    content: str
    type: str
    size: int

class Handler(Protocol):
    async def handle_message(self, message: str) -> ChatResponse: ...
    async def format_response(self, response: ChatResponse) -> str: ...
```

---

## Verification

```bash
# Check specific file
mypy src/ui/streamlit_app.py --ignore-missing-imports --disallow-untyped-defs

# Check entire module
mypy src/ui/ --ignore-missing-imports --disallow-untyped-defs
```

---

## Completion Checklist

- [x] Annotate streamlit_app.py (9 functions)
- [x] Annotate features/base_handler.py (6 functions)
- [x] Annotate features/upload_handler.py (4 functions)
- [x] Annotate features/memory_handler.py (4 functions)
- [x] Annotate features/streaming_handler.py (~2 functions)
- [x] Annotate features/mcp_handler.py (~2 functions)
- [x] Add shared type definitions (UploadedFile, AsyncIterator imports)
- [x] Verify with mypy --disallow-untyped-defs
- [x] Run test suite
- [x] Commit changes

---

## Notes

- Streamlit session_state is dynamically typed - use Any or TypedDict
- UploadedFile type from streamlit.runtime
- Handler protocol enables type-safe handler switching
- Streaming functions need AsyncGenerator annotations
