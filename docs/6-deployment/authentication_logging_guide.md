# Authentication & ngrok Deployment Logging Guide

**Version**: 2.1.0
**Last Updated**: 2025-10-26

---

## Overview

This guide explains how to use the comprehensive authentication logging system to debug login issues, monitor security events, and trace the entire authentication flow from ngrok tunnel to database verification.

---

## Quick Start: Viewing Logs

### Start with Full Logging

```bash
# Terminal 1: Start ngrok + Streamlit with logs
make deploy-ngrok

# All logs will appear in this terminal in real-time
```

### View Specific Log Levels

```bash
# Show only errors and warnings
make deploy-ngrok 2>&1 | grep -E "\[error\]|\[warning\]"

# Show only info and above (hide debug)
make deploy-ngrok 2>&1 | grep -E "\[info\]|\[warning\]|\[error\]"

# Show authentication-related logs only
make deploy-ngrok 2>&1 | grep -i "auth"
```

### Save Logs to File

```bash
# Save all logs for analysis
make deploy-ngrok 2>&1 | tee auth_debug_$(date +%Y%m%d_%H%M%S).log

# Save and view simultaneously
make deploy-ngrok 2>&1 | tee auth_debug.log
```

---

## Log Levels

The system uses **structlog** with the following levels:

| Level | Use Case | What to Look For |
|-------|----------|------------------|
| `[debug]` | Detailed tracing | Function calls, state checks, intermediate values |
| `[info]` | Normal operations | User actions, successful operations, flow markers |
| `[warning]` | Recoverable issues | Failed login attempts, fallback behavior, missing config |
| `[error]` | Critical failures | Database errors, authentication failures, exceptions |

**Set log level in `.env`:**
```bash
LOG_LEVEL=DEBUG  # Show all logs (verbose)
LOG_LEVEL=INFO   # Show info and above (default)
LOG_LEVEL=ERROR  # Show only errors
```

---

## Authentication Flow: What Gets Logged

### 1. **Configuration Loading** (`load_auth_config`)

**What happens:**
- Checks if using database or YAML auth
- Loads cookie settings
- Loads user credentials

**Key log markers:**
```
[info] ================================================================================
[info] LOADING AUTHENTICATION CONFIGURATION | config_path=config/auth_config.yaml | use_database_auth=True
[info] Using database authentication backend - loading credentials from database
[info] Authentication configuration loaded successfully
```

**What to check:**
- ✅ `use_database_auth=True` (if using database mode)
- ✅ `user_count=X` (should match expected number of users)
- ❌ `Failed to load credentials from database` (database connection issue)
- ❌ `No credentials available` (critical - no users loaded)

---

### 2. **Credentials Loading from Database** (`load_credentials_from_database`)

**What happens:**
- Queries `auth_users` table
- Retrieves password hashes
- Builds credentials dictionary

**Key log markers:**
```
[info] ================================================================================
[info] LOADING CREDENTIALS FROM DATABASE
[info] Users retrieved from database | total_users=5
[debug] Processing user | username=admin | is_active=True | has_email=True
[debug] Retrieved password hash for user | username=admin | has_password_hash=True | password_hash_length=60
[info] Credentials loaded from database successfully | total_users_loaded=5 | usernames_list=['admin', 'user1', 'user2']
```

**What to check:**
- ✅ `total_users=X` matches database
- ✅ `has_password_hash=True` for each user
- ✅ `password_hash_length=60` (bcrypt hashes are 60 chars)
- ✅ Your username appears in `usernames_list`
- ❌ `Skipping inactive user` (user exists but is disabled)
- ❌ `has_password_hash=False` (OAuth-only user, can't login with password)

---

### 3. **Login Form Rendering** (`render_login_page`)

**What happens:**
- Displays login form
- Waits for user to click Login

**Key log markers:**
```
[info] ================================================================================
[info] RENDERING LOGIN FORM - Awaiting credentials
[debug] Calling authenticator.login() with location='main'
[info] authenticator.login() returned | result_type=tuple | result_is_none=False
```

**What to check:**
- ✅ `result_is_none=False` (user clicked Login)
- ✅ `result_is_none=True` (form displayed, no submission yet)

---

### 4. **Login Attempt Detection**

**What happens:**
- User clicks Login button
- Credentials extracted from form

**Key log markers:**
```
[info] LOGIN ATTEMPT DETECTED | username=admin | name=Administrator | authentication_status=False | status_type=bool
```

**What to check:**
- ✅ `username` is correct (matches what you entered)
- ✅ `authentication_status=True` (success)
- ❌ `authentication_status=False` (failed - wrong password or user not found)
- ❌ `authentication_status=None` (empty credentials)

**⚠️ THIS IS WHERE YOUR ISSUE LIKELY IS**: If you don't see "LOGIN ATTEMPT DETECTED", it means the Login button click isn't being processed.

---

### 5. **Authentication Status Processing**

**What happens:**
- Checks if credentials are valid
- Handles success/failure/empty

**Key log markers:**
```
[info] ================================================================================
[info] PROCESSING AUTHENTICATION STATUS | authentication_status=False
[warning] AUTHENTICATION FAILED - Invalid credentials | username=admin | has_username=True
```

**What to check:**
- ✅ `authentication_status=True` → Success path
- ❌ `authentication_status=False` → Failed login (check password)
- ❌ `authentication_status=None` → Form not submitted or empty fields

---

### 6. **Database Password Verification** (`verify_user_password`)

**What happens (only if database auth is enabled):**
- Queries database for user
- Retrieves password hash
- Verifies password against hash

**Key log markers:**
```
[info] ================================================================================
[info] VERIFYING USER PASSWORD | username=admin
[debug] Querying database for user | username=admin
[debug] User record retrieved from database | username=admin | user_id=abc-123 | is_active=True | auth_method=password
[debug] Password hash retrieved, verifying... | username=admin | hash_length=60 | password_length=12
[info] Password verification completed | username=admin | password_valid=True
[info] Password verification successful | username=admin | user_id=abc-123
```

**What to check:**
- ✅ `User record retrieved from database` (user exists)
- ✅ `password_valid=True` (correct password)
- ❌ `Password verification failed - user not found` (username doesn't exist)
- ❌ `Password verification failed - no password hash` (OAuth-only user)
- ❌ `password_valid=False` (wrong password)

---

### 7. **Rate Limiting Check** (`LoginRateLimiter`)

**What happens:**
- Tracks failed login attempts
- Locks account after 5 failures

**Key log markers:**
```
[info] Rate limit check | username=admin | is_locked=False | remaining_seconds=0.0
[warning] Failed login attempt | username=admin | ip_address=unknown | attempt_count=1 | max_attempts=5
[error] User locked out due to excessive failed attempts | username=admin | lockout_duration_minutes=15 | attempt_count=5
```

**What to check:**
- ✅ `is_locked=False` (not locked out)
- ✅ `attempt_count < 5` (still have attempts left)
- ❌ `is_locked=True` → Account locked for 15 minutes
- ❌ `User locked out` → Too many failed attempts

---

## Common Issues & What to Look For

### Issue 1: "Nothing happens when I click Login"

**Expected logs (should see):**
```
[info] LOGIN ATTEMPT DETECTED | username=... | authentication_status=...
```

**If missing, check:**
1. Browser console for JavaScript errors (F12 → Console tab)
2. Streamlit component errors:
   ```bash
   make deploy-ngrok 2>&1 | grep -i "component"
   ```
3. Session state issues:
   ```bash
   make deploy-ngrok 2>&1 | grep -i "session"
   ```

**Possible causes:**
- Streamlit component not loading
- JavaScript error in browser
- Session state corrupted
- ngrok tunnel disconnected

---

### Issue 2: "Invalid credentials" but password is correct

**Expected logs:**
```
[info] VERIFYING USER PASSWORD | username=...
[info] Password verification completed | password_valid=False
```

**Check these logs:**
1. **User exists?**
   ```
   [info] User found in database | username=... | is_active=True
   ```
   - ❌ "User not found" → Username doesn't exist
   - ❌ `is_active=False` → User is disabled

2. **Password hash present?**
   ```
   [debug] has_password_hash=True | password_hash_length=60
   ```
   - ❌ `has_password_hash=False` → OAuth-only user or password not set
   - ❌ `password_hash_length=0` → Password hash is empty

3. **Password verification?**
   ```
   [info] Password verification completed | password_valid=False
   ```
   - This means bcrypt comparison failed
   - Password stored in database is different from what you're entering

**Fix:**
```bash
# Reset password using CLI
python -m src.auth.db_cli update-password --username YOUR_USERNAME --new-password "NewPassword123!"
```

---

### Issue 3: Account locked out

**Expected logs:**
```
[error] User locked out due to excessive failed attempts | username=... | lockout_duration_minutes=15
```

**Check:**
```
[info] Rate limit check | is_locked=True | remaining_seconds=742.5
```

**Fix:**
```bash
# Option 1: Wait 15 minutes

# Option 2: Reset lockout (database mode)
psql $DATABASE_URL -c "UPDATE auth_users SET locked_until = NULL, failed_login_attempts = 0 WHERE username = 'YOUR_USERNAME';"

# Option 3: Restart application (clears in-memory rate limiter)
pkill streamlit && pkill ngrok
make deploy-ngrok
```

---

### Issue 4: Database connection errors

**Expected logs:**
```
[error] Failed to load credentials from database | error=... | error_type=...
[error] Database error in get_user_by_username | error=...
```

**Check:**
1. **Database URL valid?**
   ```bash
   echo $DATABASE_URL
   # Should be: postgresql://postgres.PROJECT:PASSWORD@aws-REGION.pooler.supabase.com:5432/postgres
   ```

2. **Database reachable?**
   ```bash
   psql $DATABASE_URL -c "SELECT COUNT(*) FROM auth_users;"
   ```

3. **Tables exist?**
   ```bash
   psql $DATABASE_URL -c "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'auth_%';"
   ```

**Fix:**
- WSL2: Use **pooler** URL (port 5432), not direct connection (port 6543)
- Check `.env` for correct `DATABASE_URL`
- Verify migrations applied: `005_auth_tables.sql`, `006_email_verification.sql`, `007_2fa_and_password_history.sql`

---

## Filtering Logs by Component

### Authentication Flow Only

```bash
make deploy-ngrok 2>&1 | grep -E "streamlit_auth|db\.py|security"
```

### Login Attempts Only

```bash
make deploy-ngrok 2>&1 | grep -i "login"
```

### Password Verification Only

```bash
make deploy-ngrok 2>&1 | grep "VERIFYING USER PASSWORD" -A 20
```

### Rate Limiting Only

```bash
make deploy-ngrok 2>&1 | grep -i "rate limit\|lockout"
```

### Database Operations Only

```bash
make deploy-ngrok 2>&1 | grep -E "database|supabase"
```

### Errors and Warnings Only

```bash
make deploy-ngrok 2>&1 | grep -E "\[error\]|\[warning\]"
```

---

## Advanced Debugging

### Trace Full Login Flow

```bash
# Save all logs
make deploy-ngrok 2>&1 | tee full_login_trace.log

# Then attempt login and stop server
# Analyze the log:
cat full_login_trace.log | grep -E "LOADING|RENDERING|LOGIN ATTEMPT|PROCESSING|VERIFYING"
```

### Monitor Live Authentication Events

```bash
# Terminal 1: Start server
make deploy-ngrok

# Terminal 2: Watch logs in real-time
tail -f /tmp/streamlit_auth_debug.log | grep --line-buffered -E "\[info\]|\[warning\]|\[error\]"
```

### Debug Specific User

```bash
make deploy-ngrok 2>&1 | grep "username=YOUR_USERNAME"
```

---

## Log Analysis Checklist

When debugging a login issue, verify these logs appear in order:

- [ ] `LOADING AUTHENTICATION CONFIGURATION`
  - [ ] `use_database_auth=True`
  - [ ] `user_count > 0`
- [ ] `LOADING CREDENTIALS FROM DATABASE`
  - [ ] `Users retrieved from database | total_users=X`
  - [ ] `has_password_hash=True` for your user
- [ ] `RENDERING LOGIN FORM`
  - [ ] `authenticator.login() returned`
- [ ] `LOGIN ATTEMPT DETECTED` ← **IF MISSING, BUTTON CLICK NOT WORKING**
  - [ ] `username=YOUR_USERNAME`
  - [ ] `authentication_status` is not None
- [ ] `PROCESSING AUTHENTICATION STATUS`
  - [ ] `authentication_status=True` (success)
- [ ] `VERIFYING USER PASSWORD` (if database mode)
  - [ ] `User record retrieved from database`
  - [ ] `password_valid=True`
- [ ] `Rate limit check`
  - [ ] `is_locked=False`

---

## Environment Variables for Logging

Add to `.env`:

```bash
# Logging configuration
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR

# Show all Streamlit logs (not recommended, very verbose)
STREAMLIT_LOG_LEVEL=debug

# Database query logging (if needed)
SUPABASE_LOG_LEVEL=debug
```

---

## Integration with Analytics System

Authentication events are also logged to the PostgreSQL analytics system:

```sql
-- View recent login attempts
SELECT
    created_at,
    user_id,
    query_text,
    response_text,
    feedback_score,
    metadata_json
FROM agent_interactions
WHERE query_text LIKE 'AUTH:%'
ORDER BY created_at DESC
LIMIT 50;

-- Count login failures by user
SELECT
    user_id,
    COUNT(*) as failed_attempts
FROM agent_interactions
WHERE query_text = 'AUTH:login' AND feedback_score = 0
GROUP BY user_id
ORDER BY failed_attempts DESC;
```

---

## Getting Help

If you're still stuck after reviewing logs:

1. **Save your logs:**
   ```bash
   make deploy-ngrok 2>&1 > debug_logs_$(date +%Y%m%d_%H%M%S).log
   ```

2. **Check for errors:**
   ```bash
   cat debug_logs_*.log | grep -E "\[error\]" -B 5 -A 5
   ```

3. **Search for your username:**
   ```bash
   cat debug_logs_*.log | grep "username=YOUR_USERNAME"
   ```

4. **Look for the login attempt marker:**
   ```bash
   cat debug_logs_*.log | grep "LOGIN ATTEMPT DETECTED"
   ```

5. **If "LOGIN ATTEMPT DETECTED" is missing:**
   - Check browser console (F12 → Console)
   - Look for Streamlit component errors
   - Check ngrok tunnel is active: `make ngrok-status`

---

**Last Updated**: 2025-10-26
**Version**: 2.1.0
