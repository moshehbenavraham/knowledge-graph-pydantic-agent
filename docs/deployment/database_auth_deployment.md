# Database Authentication Deployment Guide

**Version**: v1.5.0 (Database Integration)
**Date**: 2025-10-24
**Status**: Production Ready

---

## Overview

This guide covers deploying the enhanced authentication system with database backend, including:
- ✅ Database user management (Supabase)
- ✅ Password reset flow with email tokens
- ✅ Session management
- ✅ User profile page
- ⏸️ OAuth integration (deferred to v1.6.0)

**Migration Strategy**: Hybrid approach supporting both YAML and database backends with seamless transition.

---

## Prerequisites

- ✅ Existing Base Agent installation (v1.4.0+)
- ✅ Supabase project with database access
- ✅ SMTP email server (optional, for password reset)
- ✅ Git repository access

---

## Step 1: Apply Database Migration

### 1.1 Run SQL Migration

1. **Open Supabase Dashboard** → SQL Editor
2. **Paste and execute** `src/agentic_rag/storage/migrations/sql/005_auth_tables.sql`
3. **Verify tables created**:
   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public'
   AND table_name LIKE 'auth_%';
   ```

   Expected output:
   ```
   auth_users
   auth_sessions
   auth_password_reset_tokens
   auth_oauth_accounts
   auth_roles
   auth_user_roles
   ```

4. **Verify default roles**:
   ```sql
   SELECT role_name, description FROM auth_roles;
   ```

   Expected output:
   ```
   admin   | Full system access
   user    | Standard user access
   viewer  | Read-only access
   ```

### 1.2 Test Database Functions

```sql
-- Test cleanup function
SELECT cleanup_expired_auth_sessions();

-- Test user with roles function
SELECT get_user_with_roles('00000000-0000-0000-0000-000000000000'::uuid);
```

---

## Step 2: Migrate Existing Users (YAML → Database)

### 2.1 Create Backup

```bash
# Automatic backup (recommended)
python -m src.auth.migrate_yaml_to_db

# Manual backup
cp config/auth_config.yaml config/auth_config_backup_$(date +%Y%m%d).yaml
```

### 2.2 Dry Run Migration

```bash
# Preview migration without making changes
python -m src.auth.migrate_yaml_to_db --dry-run
```

Expected output:
```
================================================================================
🔄 YAML to Database User Migration
================================================================================
✅ Created backup: config/auth_config_backup_20251024.yaml

📋 Found 1 user(s) in YAML config

🔄 Processing: admin (admin@baseagent.local)
   [DRY RUN] Would create user: admin

================================================================================
📊 Migration Summary
================================================================================
✅ Migrated:  0
⏭️  Skipped:   0
❌ Errors:    0
================================================================================

💡 This was a dry run. No changes were made.
   Run without --dry-run to perform actual migration.
```

### 2.3 Run Migration

```bash
# Perform actual migration
python -m src.auth.migrate_yaml_to_db

# Verify migration
python -m src.auth.db_cli list
```

Expected output:
```
📋 Found 1 user(s):

Username             Email                          Name                      Active   Created
----------------------------------------------------------------------------------------------------
admin                admin@baseagent.local          Administrator             ✓        2025-10-24
```

---

## Step 3: Configure Environment Variables

### 3.1 Enable Database Authentication

Add to `.env`:

```bash
# Authentication Backend
USE_DATABASE_AUTH=true  # Toggle between YAML (false) and database (true)

# Cookie Security
AUTH_COOKIE_KEY=<generate-random-key>  # Use: python -c "import secrets; print(secrets.token_urlsafe(32))"

# Password Reset
PASSWORD_RESET_URL=https://your-domain.com/reset-password  # or http://localhost:8501/reset-password for local

# Email Configuration (optional - for password reset)
EMAIL_ENABLED=true  # Set to false for local dev
EMAIL_PROVIDER=smtp  # smtp, sendgrid, mailgun, supabase
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@baseagent.local
```

### 3.2 Generate Secure Cookie Key

```bash
# Generate random key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
AUTH_COOKIE_KEY=<generated-key>
```

### 3.3 Gmail SMTP Setup (Optional)

For Gmail, use **App Passwords** (not your regular password):

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Factor Authentication
3. Create App Password: Security → 2-Step Verification → App Passwords
4. Use generated password in `SMTP_PASSWORD`

---

## Step 4: Test Authentication Features

### 4.1 Test Database Login

```bash
# Start UI
make run-ui

# Navigate to http://localhost:8501
# Login with: admin / Admin2025!Secure
```

Expected behavior:
- ✅ Login page displays with "Forgot Password?" expander (database mode)
- ✅ Successful login creates database session
- ✅ User profile section appears in sidebar

### 4.2 Test User Management CLI

```bash
# Create new user
python -m src.auth.db_cli create \
  --username john \
  --email john@example.com \
  --name "John Doe" \
  --password "SecurePass123!" \
  --role user

# List all users
python -m src.auth.db_cli list

# Get user details
python -m src.auth.db_cli get --username john

# Update user
python -m src.auth.db_cli update \
  --username john \
  --new-email john.doe@example.com

# Assign admin role
python -m src.auth.db_cli role \
  --username john \
  --action assign \
  --role admin

# View sessions
python -m src.auth.db_cli sessions --username john

# Revoke all sessions
python -m src.auth.db_cli sessions --username john --revoke

# Delete user (soft delete)
python -m src.auth.db_cli delete --username john

# Delete user (permanent)
python -m src.auth.db_cli delete --username john --permanent
```

### 4.3 Test Password Reset (if EMAIL_ENABLED=true)

1. **Request Reset**:
   - Go to login page
   - Expand "Forgot Password?"
   - Enter username or email
   - Click "Send Reset Link"

2. **Check Email**:
   - Look for email from `SMTP_FROM_EMAIL`
   - Click "Reset Password" button

3. **Complete Reset**:
   - Enter new password (2x)
   - Click "Reset Password"
   - Return to login page
   - Test new password

### 4.4 Test User Profile

1. **Login** to application
2. **Navigate** to sidebar
3. **Expand** "User Profile"
4. **Test Features**:
   - View account info
   - Change password
   - View active sessions
   - Revoke sessions

---

## Step 5: Production Deployment

### 5.1 Security Checklist

- [ ] Set `AUTH_COOKIE_KEY` to random 32+ character string
- [ ] Use HTTPS for all production deployments (ngrok, domain)
- [ ] Enable secure cookies in production (`cookie.secure: true` in auth_config.yaml)
- [ ] Configure rate limiting (already enabled, 5 attempts / 15 min)
- [ ] Review Supabase Row Level Security (RLS) policies
- [ ] Enable email for password reset (`EMAIL_ENABLED=true`)
- [ ] Use environment-specific `PASSWORD_RESET_URL`
- [ ] Rotate `AUTH_COOKIE_KEY` monthly
- [ ] Monitor failed login attempts in analytics

### 5.2 ngrok Production Setup

```bash
# Update .env
USE_DATABASE_AUTH=true
AUTH_COOKIE_KEY=<production-key>
PASSWORD_RESET_URL=https://aiwithapex.ngrok.io/reset-password

# Deploy
make deploy-ngrok

# Verify
make ngrok-status
```

### 5.3 Database Maintenance

Set up cron jobs for cleanup:

```bash
# Daily: Clean expired sessions
0 0 * * * psql $DATABASE_URL -c "SELECT cleanup_expired_auth_sessions();"

# Daily: Clean expired reset tokens
0 1 * * * psql $DATABASE_URL -c "SELECT cleanup_auth_reset_tokens();"

# Hourly: Unlock expired account lockouts
0 * * * * psql $DATABASE_URL -c "SELECT unlock_expired_auth_lockouts();"
```

---

## Step 6: Rollback Strategy

### 6.1 Switch Back to YAML

```bash
# In .env
USE_DATABASE_AUTH=false

# Restart application
make run-ui
```

Application will immediately fall back to YAML authentication.

### 6.2 Restore YAML Backup

```bash
# Restore from backup
cp config/auth_config_backup_20251024.yaml config/auth_config.yaml

# Verify
cat config/auth_config.yaml
```

---

## Troubleshooting

### Issue: "User not found" after migration

**Solution**: Verify migration completed:
```bash
python -m src.auth.db_cli list
```

If users missing, re-run migration:
```bash
python -m src.auth.migrate_yaml_to_db
```

### Issue: "Failed to load credentials from database"

**Solution**: Check database connection and table existence:
```sql
SELECT COUNT(*) FROM auth_users WHERE is_active = true;
```

Verify `.env` has correct `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`.

### Issue: Password reset email not received

**Solution**:
1. Check `EMAIL_ENABLED=true` in `.env`
2. Verify SMTP credentials
3. Check spam folder
4. View token in logs (dev mode):
   ```bash
   make run-ui | grep "Reset token"
   ```

### Issue: Session not created after login

**Solution**: Verify database session table:
```sql
SELECT COUNT(*) FROM auth_sessions WHERE revoked_at IS NULL;
```

Check logs for session creation errors:
```bash
make run-ui | grep "session"
```

---

## Architecture Reference

### Database Schema

```
auth_users (users table)
├── id (UUID, PK)
├── username (TEXT, UNIQUE)
├── email (TEXT, UNIQUE)
├── password_hash (TEXT)
├── full_name (TEXT)
├── is_active (BOOLEAN)
├── failed_login_attempts (INTEGER)
├── locked_until (TIMESTAMPTZ)
└── created_at, updated_at, deleted_at

auth_sessions (active sessions)
├── id (UUID, PK)
├── user_id (UUID, FK → auth_users)
├── session_token (TEXT, UNIQUE)
├── device_info, user_agent, ip_address
├── created_at, last_activity_at, expires_at
└── revoked_at

auth_password_reset_tokens (reset flow)
├── id (UUID, PK)
├── user_id (UUID, FK → auth_users)
├── token (TEXT, UNIQUE)
├── token_hash (TEXT)
├── created_at, expires_at
└── used_at

auth_oauth_accounts (OAuth linking)
├── id (UUID, PK)
├── user_id (UUID, FK → auth_users)
├── provider (TEXT: google, github, microsoft, apple)
├── provider_user_id (TEXT)
├── access_token, refresh_token
└── profile_data (JSONB)

auth_roles + auth_user_roles (permissions)
```

### Authentication Flow

1. **User enters credentials** → Streamlit form
2. **streamlit_auth.py loads users** → Database or YAML (based on `USE_DATABASE_AUTH`)
3. **streamlit-authenticator validates** → Bcrypt password comparison
4. **Session created** → Database (if `USE_DATABASE_AUTH=true`)
5. **Rate limiting checked** → LoginRateLimiter (5 attempts / 15 min)
6. **Analytics logged** → `agent_interactions` table
7. **User profile available** → Sidebar with password change, session management

---

## Next Steps

### Completed (v1.5.0)
- ✅ Database migration with 5 core tables
- ✅ Hybrid YAML/database authentication backend
- ✅ Password reset flow with email tokens
- ✅ User profile with password change and session management
- ✅ CLI tools for user management
- ✅ Session tracking and revocation

### Planned (v1.6.0)
- ⏸️ OAuth integration (Google, GitHub) - P3
- ⏸️ Enhanced UI/UX (password strength meter, profile pictures)
- ⏸️ 2FA/TOTP support
- ⏸️ Comprehensive test suite (database auth tests)
- ⏸️ Email templates customization

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review logs: `make run-ui | grep "auth\|session\|password"`
3. Test with CLI tools: `python -m src.auth.db_cli --help`
4. Report bugs with full error messages and steps to reproduce

---

**Last Updated**: 2025-10-24
**Version**: 1.5.0 (Database Authentication Integration)
