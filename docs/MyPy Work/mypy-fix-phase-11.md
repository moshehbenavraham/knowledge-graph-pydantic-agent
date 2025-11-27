# MyPy Fix Phase 11: Type Annotations - auth/ Module

**Status**: Not Started
**Estimated Errors**: 25
**Files**: 8
**Prerequisites**: Phase 10 complete

---

## Objective

Add missing type annotations to the `src/auth/` module (authentication and authorization).

---

## Files to Annotate

| File | Missing Annotations |
|------|---------------------|
| src/auth/db_cli.py | 9 |
| src/auth/db.py | ~5 |
| src/auth/streamlit_auth.py | ~4 |
| src/auth/password_reset.py | ~3 |
| src/auth/user_manager.py | ~2 |
| src/auth/security.py | ~2 |
| src/auth/email_verification.py | ~1 |
| src/auth/captcha.py | ~1 |

---

## Auth-Specific Patterns

### Database Operations
```python
# Before
async def create_user(username, email, password_hash):
    ...

# After
async def create_user(
    username: str,
    email: str,
    password_hash: str
) -> UserRecord:
    ...
```

### Authentication Functions
```python
# Before
def verify_password(plain_password, hashed_password):
    ...

# After
def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    ...
```

### Session Management
```python
# Before
def create_session(user_id, expires_at):
    ...

# After
from datetime import datetime

def create_session(
    user_id: str,
    expires_at: datetime
) -> Session:
    ...
```

### CLI Commands
```python
# Before
def create_user_command(username, email, password, role):
    ...

# After
import click

@click.command()
def create_user_command(
    username: str,
    email: str,
    password: str,
    role: str
) -> None:
    ...
```

---

## File-by-File Strategy

### db_cli.py (9 annotations)
- CLI command handlers
- User CRUD operations
- Role management
- Session operations

### db.py (~5 annotations)
- Database connection
- Query execution
- Transaction handling
- Schema operations

### streamlit_auth.py (~4 annotations)
- Authentication flow
- Session state
- Cookie handling
- Login/logout

### password_reset.py (~3 annotations)
- Token generation
- Email sending
- Password update
- Token validation

### user_manager.py (~2 annotations)
- YAML user operations
- Password hashing
- User lookup

### security.py (~2 annotations)
- Rate limiting
- Lockout logic
- Attempt tracking

---

## Type Definitions to Add

```python
from typing import TypedDict
from dataclasses import dataclass
from datetime import datetime

@dataclass
class UserRecord:
    id: str
    username: str
    email: str
    password_hash: str
    role: str
    created_at: datetime
    updated_at: datetime

@dataclass
class Session:
    id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    is_active: bool

class AuthResult(TypedDict):
    success: bool
    user: UserRecord | None
    error: str | None

class PasswordResetToken(TypedDict):
    token: str
    user_id: str
    expires_at: datetime
```

---

## Verification

```bash
# Check specific file
mypy src/auth/db_cli.py --ignore-missing-imports --disallow-untyped-defs

# Check entire module
mypy src/auth/ --ignore-missing-imports --disallow-untyped-defs
```

---

## Completion Checklist

- [ ] Annotate db_cli.py (9 functions)
- [ ] Annotate db.py (~5 functions)
- [ ] Annotate streamlit_auth.py (~4 functions)
- [ ] Annotate password_reset.py (~3 functions)
- [ ] Annotate user_manager.py (~2 functions)
- [ ] Annotate security.py (~2 functions)
- [ ] Annotate remaining files
- [ ] Add shared type definitions
- [ ] Verify with mypy --disallow-untyped-defs
- [ ] Run test suite
- [ ] Commit changes

---

## Notes

- Password hashes should always be str, never bytes
- Session tokens use secrets.token_urlsafe()
- Click decorators have their own type handling
- Be careful with security-sensitive return types
