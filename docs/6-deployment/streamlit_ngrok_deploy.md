# Streamlit + ngrok Deployment Guide

**Version**: 2.1.0
**Last Updated**: 2025-10-26

---

## Overview

Deploy Luminari Agent with public HTTPS access via ngrok tunnel.

**Security Architecture**:
```
Internet -> ngrok (HTTP Basic Auth) -> Streamlit (Database Auth) -> Luminari Agent
```

**Features**:
- Two-layer authentication (ngrok + Streamlit)
- Database-backed user management (PostgreSQL/Supabase)
- OAuth 2.0 login (Google, GitHub, Microsoft, Apple)
- 2FA/TOTP with backup codes
- Password security (breach detection, history, strength validation)
- Email verification and password reset
- User profile and admin dashboards

---

## Quick Start (10 Minutes)

```bash
# 1. Apply database migrations
psql $DATABASE_URL -f src/agentic_rag/storage/migrations/sql/005_auth_tables.sql
psql $DATABASE_URL -f src/agentic_rag/storage/migrations/sql/006_email_verification.sql
psql $DATABASE_URL -f src/agentic_rag/storage/migrations/sql/007_2fa_and_password_history.sql

# 2. Generate auth keys
python -c "import secrets; print('AUTH_COOKIE_KEY=' + secrets.token_urlsafe(32))" >> .env

# 3. Migrate users
python -m src.auth.migrate_yaml_to_db

# 4. Configure ngrok
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN

# 5. Deploy
make deploy-ngrok

# 6. Get URL
make ngrok-status
```

---

## Prerequisites

**Required**:
- Luminari Agent v1.5.0+
- Supabase account with project
- Neo4j Aura account with database
- ngrok account (free tier works)
- Python 3.11+

**Optional**:
- OAuth app credentials (Google, GitHub, Microsoft, Apple)
- SMTP service (Gmail, SendGrid, etc.)
- ngrok Personal/Pro (for custom domains)

---

## Step 1: ngrok Setup

### Install ngrok

**Linux/macOS**:
```bash
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
  | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
  | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Or with homebrew (macOS)
brew install ngrok
```

### Configure ngrok

```bash
# Add authtoken
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN

# Verify
ngrok version
```

### Create ngrok config

Edit `~/.config/ngrok/ngrok.yml`:

**ngrok v2**:
```yaml
version: 2
authtoken: YOUR_NGROK_AUTHTOKEN
tunnels:
  base-agent-ui:
    proto: http
    addr: 8501
    domain: your-domain.ngrok.io  # Optional: Personal/Pro only
    inspect: true
    auth: "username:password"  # HTTP Basic Auth
```

**ngrok v3**:
```yaml
version: "3"
agent:
  authtoken: YOUR_NGROK_AUTHTOKEN
tunnels:
  base-agent-ui:
    proto: http
    addr: 8501
    domain: your-domain.ngrok.io  # Optional: Personal/Pro only
    inspect: true
    basic_auth:
      - "username:password"  # HTTP Basic Auth
```

Generate secure password:
```bash
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

---

## Step 2: Database Setup

### Supabase

1. Create project at [supabase.com](https://supabase.com)
2. Get credentials from Settings -> Database:
   - Project URL: `https://your-project.supabase.co`
   - Service Role Key (API settings)
   - Connection String (use Session pooler for WSL2):
     ```
     postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-[REGION].pooler.supabase.com:5432/postgres
     ```

3. Apply migrations via SQL Editor:
   - `005_auth_tables.sql` (core auth tables)
   - `006_email_verification.sql` (email verification)
   - `007_2fa_and_password_history.sql` (2FA, CAPTCHA, breach detection)
   - `008_oauth_analytics.sql` (OAuth analytics - optional)

4. Verify tables created:
   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public' AND table_name LIKE 'auth_%';
   ```

### Neo4j Aura

1. Create database at [neo4j.com/cloud/aura](https://neo4j.com/cloud/aura)
2. Download credentials file
3. Get connection details:
   - URI: `neo4j+s://xxxxx.databases.neo4j.io`
   - Username: `neo4j`
   - Password: (from credentials file)

4. Initialize:
   ```bash
   make neo4j-init
   ```

---

## Step 3: Environment Configuration

Edit `.env`:

```bash
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_key
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-[REGION].pooler.supabase.com:5432/postgres

# Neo4j
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
NEO4J_ENCRYPTED=true

# LLM
LLM_PROVIDER=openai
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-5-mini

# Embedding
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=your_api_key
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# ngrok
NGROK_AUTHTOKEN=your_ngrok_authtoken
NGROK_DOMAIN=your-domain.ngrok.io  # Optional

# Authentication
USE_DATABASE_AUTH=true
AUTH_COOKIE_KEY=  # Generate below
```

Generate auth keys:
```bash
python -c "import secrets; print('AUTH_COOKIE_KEY=' + secrets.token_urlsafe(32))" >> .env
python -c "from cryptography.fernet import Fernet; print('OAUTH_ENCRYPTION_KEY=' + Fernet.generate_key().decode())" >> .env
```

---

## Step 4: Authentication

### Database Mode (Recommended)

```bash
# Migrate users from YAML
python -m src.auth.migrate_yaml_to_db

# Verify
python -m src.auth.db_cli list
```

### Optional: OAuth Login

Add to `.env`:
```bash
OAUTH_ENABLED=true
OAUTH_ENCRYPTION_KEY=your_fernet_key

# Google
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=https://your-domain.ngrok.io

# GitHub
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GITHUB_REDIRECT_URI=https://your-domain.ngrok.io
```

Setup OAuth apps:
- Google: [console.cloud.google.com](https://console.cloud.google.com) -> Credentials
- GitHub: [github.com/settings/developers](https://github.com/settings/developers) -> OAuth Apps

### Optional: Email (Password Reset)

Add to `.env`:
```bash
EMAIL_ENABLED=true
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your_app_password  # Gmail: Use App Password with 2FA
SMTP_FROM_EMAIL=noreply@luminariagent.local
PASSWORD_RESET_URL=https://your-domain.ngrok.io/reset-password
VERIFICATION_URL=https://your-domain.ngrok.io
```

### Optional: 2FA/TOTP

Add to `.env`:
```bash
TOTP_ISSUER_NAME=Luminari Agent
BACKUP_CODE_COUNT=10
BACKUP_CODE_EXPIRY_DAYS=90
```

### Optional: CAPTCHA

Add to `.env`:
```bash
CAPTCHA_ENABLED=true
CAPTCHA_THRESHOLD=3
CAPTCHA_PROVIDER=hcaptcha
HCAPTCHA_SITE_KEY=your_site_key
HCAPTCHA_SECRET_KEY=your_secret_key
```

### Optional: Password Security

Add to `.env`:
```bash
PASSWORD_HISTORY_COUNT=5
PASSWORD_HISTORY_ENABLED=true
BREACH_DETECTION_ENABLED=true
BREACH_CHECK_ON_REGISTRATION=true
BREACH_CHECK_ON_PASSWORD_CHANGE=true
```

### YAML Mode (Legacy)

For users not using database backend:

```bash
# In .env
USE_DATABASE_AUTH=false

# User management
python -m src.auth.user_manager create --username USER --email EMAIL --password PASS
python -m src.auth.user_manager list
python -m src.auth.user_manager update-password --username USER --password PASS
python -m src.auth.user_manager delete --username USER
python -m src.auth.hash_password "YourPassword"  # Generate hash
```

Edit `config/auth_config.yaml`:
```yaml
cookie:
  key: "CHANGE_IN_PRODUCTION"  # Generate: secrets.token_urlsafe(32)
  expiry_days: 30
  secure: false  # Set true in production

credentials:
  usernames:
    admin:
      email: "max@aiwithapex.com"
      name: "Administrator"
      password: "$2b$12$..."  # Use hash_password.py

config:
  auto_logout: true
  auto_logout_minutes: 30
  bcrypt_log_rounds: 12
```

**YAML Limitations**: No session tracking, password reset, OAuth, 2FA, or admin analytics.

---

## Step 5: Deploy

```bash
# Start deployment
make deploy-ngrok

# Get public URL
make ngrok-status
```

Access your public URL (e.g., `https://your-domain.ngrok.io`):
1. Enter ngrok credentials (HTTP Basic Auth)
2. Enter Streamlit credentials (default: admin/Admin2025!Secure)

**Change default passwords immediately!**

---

## User Management

### Database Mode

```bash
# Create user
python -m src.auth.db_cli create --username USER --email EMAIL --name NAME --password PASS --role ROLE

# List users
python -m src.auth.db_cli list

# Update
python -m src.auth.db_cli update --username USER --new-email EMAIL
python -m src.auth.db_cli update-password --username USER --new-password PASS

# Roles
python -m src.auth.db_cli role --username USER --action assign --role admin

# Sessions
python -m src.auth.db_cli sessions --username USER
python -m src.auth.db_cli sessions --username USER --revoke

# Delete
python -m src.auth.db_cli delete --username USER
python -m src.auth.db_cli delete --username USER --permanent
```

### Admin Features

**Require 2FA for user**:
```bash
python -c "import asyncio; from src.auth.db import set_2fa_requirement; asyncio.run(set_2fa_requirement('USERNAME', True))"
```

**OAuth Analytics**: Apply migration 008, access admin dashboard

---

## Verification

```bash
# Check ngrok status
make ngrok-status

# Test public URL
curl https://your-domain.ngrok.io  # Should get 401 or redirect

# Verify database
python -m src.auth.db_cli list

# Check sessions
python -m src.auth.db_cli sessions --username admin
```

**Test in browser**:
- [ ] ngrok auth prompt appears
- [ ] Login page displays
- [ ] Login succeeds with correct credentials
- [ ] User profile appears in sidebar
- [ ] Logout works
- [ ] Session persists across refreshes
- [ ] Password change works
- [ ] OAuth buttons appear (if enabled)
- [ ] 2FA setup appears (if required)

---

## Monitoring

### Daily

```bash
# Check tunnel
make ngrok-status

# View logs
make ngrok-logs

# Clean expired data
psql $DATABASE_URL -c "SELECT cleanup_expired_auth_sessions();"
psql $DATABASE_URL -c "SELECT cleanup_auth_reset_tokens();"
```

### Automated (Cron)

```bash
# Daily cleanup (midnight)
0 0 * * * psql $DATABASE_URL -c "SELECT cleanup_expired_auth_sessions();"

# Hourly OAuth analytics refresh
0 * * * * psql $DATABASE_URL -c "SELECT refresh_oauth_analytics_views();"
```

### Analytics Queries

```sql
-- Active sessions
SELECT COUNT(*) FROM auth_sessions WHERE revoked_at IS NULL;

-- Failed logins
SELECT COUNT(*) FROM auth_captcha_challenges WHERE success = false;

-- OAuth usage
SELECT provider, COUNT(*) FROM auth_oauth_accounts GROUP BY provider;

-- Locked accounts
SELECT username, locked_until FROM auth_users WHERE locked_until > NOW();
```

---

## Troubleshooting

### ngrok Issues

**"ngrok not found"**:
```bash
sudo apt install ngrok
```

**"Invalid authtoken"**:
```bash
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
```

**Port conflict**:
```bash
pkill ngrok
make deploy-ngrok
```

**Can't access URL**:
```bash
# Check tunnel
make ngrok-status

# Check Streamlit
curl http://localhost:8501
```

### Database Issues

**Connection failed (WSL2)**:
```bash
# Use Session pooler URL (port 5432), not direct connection (port 6543)
# In .env:
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-[REGION].pooler.supabase.com:5432/postgres
```

**Table not found**:
```bash
# Apply migrations in order
psql $DATABASE_URL -f src/agentic_rag/storage/migrations/sql/005_auth_tables.sql
psql $DATABASE_URL -f src/agentic_rag/storage/migrations/sql/006_email_verification.sql
psql $DATABASE_URL -f src/agentic_rag/storage/migrations/sql/007_2fa_and_password_history.sql
```

### Auth Issues

**Login fails**:
```bash
# Check user exists
python -m src.auth.db_cli list

# Reset password
python -m src.auth.db_cli update-password --username USER --new-password PASS

# Unlock account
psql $DATABASE_URL -c "UPDATE auth_users SET locked_until = NULL WHERE username = 'USER';"
```

**OAuth fails**:
```bash
# Verify redirect URI matches
echo $GOOGLE_REDIRECT_URI  # Should match Google Console

# Check credentials
echo $GOOGLE_CLIENT_ID
echo $OAUTH_ENABLED
```

**2FA codes rejected**:
```bash
# Check server time sync
timedatectl status
sudo timedatectl set-ntp true
```

**Email not received**:
```bash
# For dev, disable email and check logs
# In .env: EMAIL_ENABLED=false
# Token appears in logs
```

**YAML Mode: Config not found**:
```bash
ls config/auth_config.yaml
cp config/auth_config_backup.yaml config/auth_config.yaml
```

**YAML Mode: Session expires quickly**:
```yaml
# Edit config/auth_config.yaml
cookie:
  expiry_days: 90  # Increase from 30
config:
  auto_logout_minutes: 120  # Increase from 30
```

---

## Rollback

### To YAML Mode

```bash
# Stop app
pkill streamlit && pkill ngrok

# Disable database auth
# In .env: USE_DATABASE_AUTH=false

# Restore YAML backup (if needed)
cp config/auth_config_backup_YYYYMMDD.yaml config/auth_config.yaml

# Restart
make deploy-ngrok
```

### Emergency Access

```bash
# Reset user
psql $DATABASE_URL -c "UPDATE auth_users SET locked_until = NULL, failed_login_attempts = 0 WHERE username = 'admin';"

# Reset password
python -m src.auth.db_cli update-password --username admin --new-password "NewPass123!"

# Create emergency admin
python -m src.auth.db_cli create --username emergency --email emergency@local.com --name "Emergency" --password "EmergencyPass123!" --role admin
```

### Backup/Restore

```bash
# Backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Auth tables only
pg_dump $DATABASE_URL -t 'auth_*' > auth_backup_$(date +%Y%m%d).sql

# Restore
psql $DATABASE_URL < backup_YYYYMMDD.sql
```

---

## Security Checklist

**Production Requirements**:
- [ ] Strong passwords (16+ characters)
- [ ] Unique AUTH_COOKIE_KEY (32+ characters)
- [ ] HTTPS enforced (ngrok provides SSL)
- [ ] Two-layer auth enabled
- [ ] Email verification enabled
- [ ] Password strength enforced
- [ ] Breach detection enabled
- [ ] Rate limiting enabled (automatic)
- [ ] 2FA required for admins
- [ ] Regular backups scheduled
- [ ] Monitoring active sessions
- [ ] .env not in git
- [ ] Monthly key rotation

**Enable all security features**:
```bash
# In .env
USE_DATABASE_AUTH=true
EMAIL_ENABLED=true
OAUTH_ENABLED=true  # Optional
CAPTCHA_ENABLED=true
PASSWORD_HISTORY_ENABLED=true
BREACH_DETECTION_ENABLED=true
```

---

## FAQ

**Q: Minimum ngrok plan?**
A: Free plan works. Custom domains require Personal ($8/mo) or Pro ($20/mo).

**Q: Custom domain?**
A: Yes, with ngrok Personal/Pro. Configure in `~/.config/ngrok/ngrok.yml`.

**Q: Disable OAuth after enabling?**
A: Set `OAUTH_ENABLED=false`. OAuth users remain in database.

**Q: Users with both password and OAuth?**
A: Yes, called "hybrid" mode. Users can log in either way.

**Q: Reset forgotten password?**
A: With `EMAIL_ENABLED=true`, use "Forgot Password?" on login. Otherwise use CLI.

**Q: Lost 2FA authenticator?**
A: Use backup codes. If lost, admin must disable 2FA via database.

**Q: Switch between Supabase and self-hosted PostgreSQL?**
A: Update `DATABASE_URL`. Ensure pgvector extension installed.

**Q: Deploy without ngrok?**
A: Alternatives: Cloudflare Tunnel, AWS/GCP/Azure, Nginx + Let's Encrypt.

**Q: Concurrent users?**
A: Tested up to 100 on free Supabase. Upgrade Pro ($25/mo) for more.

**Q: Improve performance?**
A: Enable Redis caching, refresh analytics hourly (not on-demand), clean old sessions, use connection pooling (automatic in v1.5.0+).

---

## Additional Resources

**Documentation**:
- Full project docs: `CLAUDE.md`
- Implementation details: `docs/deployment/v2.1.0_implementation_summary.md`

**Database Migrations**:
- `005_auth_tables.sql` - Core auth tables
- `006_email_verification.sql` - Email verification
- `007_2fa_and_password_history.sql` - 2FA, CAPTCHA, breach detection
- `008_oauth_analytics.sql` - OAuth analytics

**Monitoring**:
- ngrok dashboard: `http://localhost:4040`
- Tunnel status: `make ngrok-status`
- Access logs: `make ngrok-logs`

---

**Last Updated**: 2025-10-26
**Version**: 2.1.0
**Status**: Production Ready
