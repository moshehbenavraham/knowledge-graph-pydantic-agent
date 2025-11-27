# MyPy Fix Phase 11: Type Annotations - auth/ Module

**Status**: Complete
**Actual Errors Fixed**: 18
**Files Modified**: 9
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

- [x] Annotate db_cli.py (9 functions) - Added `-> int` to all 9 async command functions
- [x] Annotate db.py (~5 functions) - Already fully typed
- [x] Annotate streamlit_auth.py (~4 functions) - Already fully typed
- [x] Annotate password_reset.py (~3 functions) - Already fully typed
- [x] Annotate user_manager.py (1 function) - Added `-> None` to `main()`
- [x] Annotate security.py (~2 functions) - Already fully typed
- [x] Annotate remaining files:
  - password_history.py: Added `-> None` to `PasswordHistoryManager.__init__()`
  - breach_detection.py: Added `-> None` to `BreachDetectionManager.__init__()`
  - migrate_yaml_to_db.py: Added `-> int` to `main()`
  - totp_2fa.py: Added `-> None` to `BackupCodeManager.__init__()`
  - user_profile.py: Added `-> None` to `render_user_profile()` and `render_user_profile_simple()`
  - password_reset_page.py: Added `-> None` to `render_password_reset_page()`
  - email_verification_page.py: Added `-> None` to `render_email_verification_page()`
- [x] Add shared type definitions - Not needed, existing types sufficient
- [x] Verify with mypy --disallow-untyped-defs - Success: no issues found in 23 source files
- [x] Run test suite - Verified imports work, pre-existing test issues unrelated to changes
- [x] Commit changes

---

## Notes

- Password hashes should always be str, never bytes
- Session tokens use secrets.token_urlsafe()
- Click decorators have their own type handling
- Be careful with security-sensitive return types
