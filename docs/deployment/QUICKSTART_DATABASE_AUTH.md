# Quick Start: Database Authentication

**Goal**: Migrate from YAML to database authentication in 10 minutes.

---

## Prerequisites

- ✅ Base Agent v1.4.0+ installed
- ✅ Supabase project accessible
- ✅ `.env` file configured

---

## 5-Step Quick Start

### Step 1: Apply SQL Migration (2 minutes)

1. Open **Supabase Dashboard** → **SQL Editor**
2. Copy contents of `src/agentic_rag/storage/migrations/sql/005_auth_tables.sql`
3. Paste and click **Run**
4. Verify: Should see "Success. No rows returned"

### Step 2: Migrate Existing Users (1 minute)

```bash
# Migrate users (with automatic backup)
python -m src.auth.migrate_yaml_to_db

# Verify
python -m src.auth.db_cli list
```

Expected output:
```
📋 Found 1 user(s):

Username   Email                   Name            Active  Created
-----------------------------------------------------------------
admin      admin@baseagent.local   Administrator   ✓       2025-10-24
```

### Step 3: Enable Database Auth (1 minute)

Add to `.env`:

```bash
USE_DATABASE_AUTH=true

# Generate random key: python -c "import secrets; print(secrets.token_urlsafe(32))"
AUTH_COOKIE_KEY=<your-random-key>
```

### Step 4: Test Login (1 minute)

```bash
make run-ui
```

Navigate to http://localhost:8501 and login with existing credentials.

**What's New**:
- ✅ "Forgot Password?" expander on login page
- ✅ User Profile section in sidebar
- ✅ Database session created on login

### Step 5: (Optional) Configure Email (5 minutes)

For password reset functionality, add to `.env`:

```bash
EMAIL_ENABLED=true
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@baseagent.local
PASSWORD_RESET_URL=http://localhost:8501/reset-password
```

**Gmail Setup**:
1. Enable 2FA: [Google Account Security](https://myaccount.google.com/security)
2. Create App Password: Security → 2-Step Verification → App Passwords
3. Use generated password in `SMTP_PASSWORD`

---

## Verification Checklist

- [ ] SQL migration applied (5 tables created)
- [ ] Users migrated to database
- [ ] `USE_DATABASE_AUTH=true` in `.env`
- [ ] Can login with existing password
- [ ] User profile appears in sidebar
- [ ] (Optional) Email reset works

---

## Next Steps

### User Management

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

# View user details
python -m src.auth.db_cli get --username john
```

### User Profile Features

1. **Change Password**:
   - Sidebar → User Profile → Change Password
   - Enter current password + new password

2. **View Sessions**:
   - Sidebar → User Profile → Active Sessions
   - See all logged-in devices

3. **Revoke Sessions**:
   - Individual: Click "Revoke This Session"
   - All: Click "Revoke All Sessions" (logs out everywhere)

---

## Rollback (if needed)

```bash
# In .env
USE_DATABASE_AUTH=false

# Restart
make run-ui
```

Immediately switches back to YAML authentication.

---

## Troubleshooting

**Q: "User not found" after migration**

```bash
# Re-run migration
python -m src.auth.migrate_yaml_to_db
```

**Q: "Failed to load credentials"**

Check Supabase connection:
```bash
# Verify .env has correct values
grep SUPABASE .env

# Test database
python -m src.auth.db_cli list
```

**Q: Password reset email not received**

Set in `.env`:
```bash
EMAIL_ENABLED=false  # Disable for local dev
```

Reset tokens will appear in logs:
```bash
make run-ui | grep "Reset token"
```

---

## Full Documentation

For complete details, see:
- **Deployment Guide**: `docs/deployment/database_auth_deployment.md`
- **Implementation Summary**: `docs/deployment/v1.5.0_implementation_summary.md`

---

**Last Updated**: 2025-10-24
**Status**: Production Ready
**Version**: 1.5.0
