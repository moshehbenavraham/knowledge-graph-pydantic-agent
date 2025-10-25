# OAuth Authentication Setup Guide

Complete guide for setting up OAuth 2.0 authentication with Google and GitHub for the Base Agent.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Google OAuth Setup](#google-oauth-setup)
- [GitHub OAuth Setup](#github-oauth-setup)
- [Environment Configuration](#environment-configuration)
- [Testing OAuth Flow](#testing-oauth-flow)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

---

## Prerequisites

1. **Database Authentication Enabled**: OAuth requires database backend
   ```bash
   USE_DATABASE_AUTH=true
   ```

2. **Database Schema Applied**: Ensure auth tables exist
   ```bash
   # Apply schema via Supabase Dashboard SQL Editor
   cat src/agentic_rag/storage/migrations/sql/005_auth_tables.sql
   ```

3. **Dependencies Installed**: authlib and httpx required
   ```bash
   pip install authlib httpx
   # OR (if using uv)
   uv pip install authlib httpx
   ```

4. **OAuth Encryption Key**: Generate encryption key for token storage
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

---

## Quick Start

**5-minute setup for local development:**

1. **Generate encryption key:**
   ```bash
   export OAUTH_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
   ```

2. **Set up Google OAuth** (or skip to GitHub):
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create project → APIs & Services → Credentials → Create OAuth 2.0 Client ID
   - Application type: Web application
   - Authorized redirect URI: `http://localhost:8501`
   - Copy Client ID and Client Secret

3. **Update .env:**
   ```bash
   USE_DATABASE_AUTH=true
   OAUTH_ENABLED=true
   OAUTH_ENCRYPTION_KEY=your_generated_key_from_step_1
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   GOOGLE_REDIRECT_URI=http://localhost:8501
   ```

4. **Start app:**
   ```bash
   make run-ui
   ```

5. **Test login:**
   - Navigate to http://localhost:8501
   - Click "🔵 Google" button
   - Authorize with your Google account
   - You'll be redirected back and logged in automatically

---

## Google OAuth Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name: "Base Agent OAuth"
4. Click "Create"

### Step 2: Enable OAuth Consent Screen

1. Navigate to "APIs & Services" → "OAuth consent screen"
2. Choose user type:
   - **Internal** (for Google Workspace organizations only)
   - **External** (for general use - requires verification for production)
3. Fill in application information:
   - **App name**: Base Agent
   - **User support email**: your-email@gmail.com
   - **Developer contact**: your-email@gmail.com
4. Add scopes:
   - `openid`
   - `email`
   - `profile`
5. Save and continue

### Step 3: Create OAuth 2.0 Credentials

1. Navigate to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth 2.0 Client ID"
3. Application type: **Web application**
4. Name: "Base Agent Web Client"
5. Add Authorized redirect URIs:
   - **Local development**: `http://localhost:8501`
   - **ngrok deployment**: `https://your-domain.ngrok.io`
   - **Production**: `https://your-production-domain.com`
6. Click "Create"
7. Copy the Client ID and Client Secret

### Step 4: Configure Environment

Add to `.env`:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=123456789-abcdefg.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxx
GOOGLE_REDIRECT_URI=http://localhost:8501
```

---

## GitHub OAuth Setup

### Step 1: Create GitHub OAuth App

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "OAuth Apps" → "New OAuth App"
3. Fill in application information:
   - **Application name**: Base Agent
   - **Homepage URL**: `http://localhost:8501` (or your production URL)
   - **Application description**: Advanced RAG AI Assistant
   - **Authorization callback URL**: `http://localhost:8501`
     - For ngrok: `https://your-domain.ngrok.io`
     - For production: `https://your-production-domain.com`
4. Click "Register application"

### Step 2: Generate Client Secret

1. On the OAuth App page, click "Generate a new client secret"
2. Copy the Client Secret (you won't be able to see it again!)
3. Copy the Client ID

### Step 3: Configure Environment

Add to `.env`:

```bash
# GitHub OAuth
GITHUB_CLIENT_ID=Iv1.xxxxxxxxxxxx
GITHUB_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_REDIRECT_URI=http://localhost:8501
```

---

## Environment Configuration

### Complete OAuth Configuration

Update `.env` with all OAuth settings:

```bash
# ===== AUTHENTICATION =====
USE_DATABASE_AUTH=true
AUTH_COOKIE_KEY=your_random_32_char_string

# ===== OAUTH AUTHENTICATION =====
OAUTH_ENABLED=true
OAUTH_ENCRYPTION_KEY=your_fernet_key_here

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8501

# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GITHUB_REDIRECT_URI=http://localhost:8501
```

### Generate Encryption Keys

```bash
# Generate AUTH_COOKIE_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate OAUTH_ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**IMPORTANT**: Never commit these keys to git! They are in `.gitignore` by default.

---

## Testing OAuth Flow

### Local Testing (localhost:8501)

1. **Start the application:**
   ```bash
   make run-ui
   ```

2. **Navigate to login page:**
   ```
   http://localhost:8501
   ```

3. **Test Google OAuth:**
   - Click "🔵 Google" button
   - Sign in with your Google account
   - Authorize Base Agent to access your profile
   - You should be redirected back to the app and logged in

4. **Test GitHub OAuth:**
   - Log out from the app
   - Click "⚫ GitHub" button
   - Sign in with your GitHub account
   - Authorize Base Agent
   - You should be redirected back and logged in

5. **Verify user creation:**
   ```bash
   # Check if OAuth user was created
   python -m src.auth.db_cli list
   ```

### ngrok Testing (with HTTPS)

1. **Update redirect URIs in Google/GitHub:**
   - Google Cloud Console → Update redirect URI to `https://your-domain.ngrok.io`
   - GitHub OAuth App → Update callback URL to `https://your-domain.ngrok.io`

2. **Update `.env`:**
   ```bash
   GOOGLE_REDIRECT_URI=https://your-domain.ngrok.io
   GITHUB_REDIRECT_URI=https://your-domain.ngrok.io
   ```

3. **Deploy with ngrok:**
   ```bash
   make deploy-ngrok
   ```

4. **Test OAuth flow** as described above, using the ngrok URL

---

## Production Deployment

### 1. Update OAuth App Settings

**Google Cloud Console:**
- Add production redirect URI: `https://your-domain.com`
- Update authorized JavaScript origins: `https://your-domain.com`

**GitHub OAuth App:**
- Update callback URL: `https://your-domain.com`
- Update homepage URL: `https://your-domain.com`

### 2. Update Environment Variables

```bash
# Production .env
USE_DATABASE_AUTH=true
OAUTH_ENABLED=true

# Use secure random keys (generate new ones for production!)
AUTH_COOKIE_KEY=<new_random_key>
OAUTH_ENCRYPTION_KEY=<new_fernet_key>

# Production redirect URIs
GOOGLE_REDIRECT_URI=https://your-domain.com
GITHUB_REDIRECT_URI=https://your-domain.com
```

### 3. Enable HTTPS

OAuth requires HTTPS in production. Options:

- **ngrok Pro**: Custom domains with HTTPS
- **Cloudflare Tunnel**: Free HTTPS tunneling
- **Nginx + Let's Encrypt**: Self-hosted SSL
- **Cloud platforms**: AWS/GCP/Azure with managed SSL

### 4. Security Checklist

- [ ] Generated new encryption keys for production (don't reuse dev keys!)
- [ ] Updated redirect URIs to production domain
- [ ] Enabled HTTPS/SSL
- [ ] Set secure cookie settings (`secure: true` in auth_config.yaml)
- [ ] Reviewed OAuth scopes (minimize requested permissions)
- [ ] Tested OAuth flow end-to-end
- [ ] Set up monitoring for OAuth failures

---

## Troubleshooting

### "OAuth credentials not configured"

**Error:**
```
ValueError: OAuth credentials not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in environment.
```

**Solution:**
- Ensure `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in `.env`
- Restart the application after updating `.env`
- Verify credentials are correct (no extra spaces)

---

### "Redirect URI mismatch"

**Error from Google/GitHub:**
```
Error: redirect_uri_mismatch
```

**Solution:**
- Verify redirect URI in `.env` matches exactly what's configured in Google Cloud Console / GitHub OAuth App
- Check for trailing slashes (use `http://localhost:8501`, NOT `http://localhost:8501/`)
- Update the redirect URI in the OAuth provider console to match your deployment

---

### "Invalid state parameter (CSRF protection)"

**Error in app:**
```
OAuth error: Invalid state parameter (CSRF protection)
```

**Solution:**
- This is a security check failure
- Clear browser cookies and try again
- Ensure your browser allows cookies for the application
- Don't bookmark OAuth callback URLs (they contain one-time codes)

---

### "OAUTH_ENCRYPTION_KEY not set"

**Error:**
```
ValueError: OAUTH_ENCRYPTION_KEY not set
```

**Solution:**
```bash
# Generate key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to .env
OAUTH_ENCRYPTION_KEY=generated_key_here

# Restart app
make run-ui
```

---

### OAuth buttons not appearing

**Symptoms:**
- Login page doesn't show Google/GitHub buttons

**Solution:**
1. Check `USE_DATABASE_AUTH=true` in `.env`
2. Check `OAUTH_ENABLED=true` in `.env`
3. Verify OAuth credentials are set:
   ```bash
   echo $GOOGLE_CLIENT_ID
   echo $GITHUB_CLIENT_ID
   ```
4. Restart the application

---

### User not created after OAuth login

**Symptoms:**
- OAuth flow succeeds but user is not logged in

**Check logs:**
```bash
# Run UI and check logs
make run-ui | grep "OAuth"
```

**Common issues:**
- Database connection error (check Supabase credentials)
- Email not provided by OAuth provider (required for user creation)
- Database schema not applied (run `005_auth_tables.sql`)

---

## Security Considerations

### Token Storage

- **Encryption**: All OAuth tokens encrypted with Fernet before storage
- **Access tokens**: Encrypted in `auth_oauth_accounts.access_token`
- **Refresh tokens**: Encrypted in `auth_oauth_accounts.refresh_token`
- **Encryption key**: Must be kept secret (use environment variable, never commit)

### CSRF Protection

- **State parameter**: Random 32-byte token generated for each OAuth flow
- **Validation**: State is verified on callback to prevent CSRF attacks
- **Session storage**: State stored in Streamlit session_state during flow

### Scope Minimization

**Google:**
- `openid`: User identifier
- `email`: Email address (required for account creation)
- `profile`: Name and avatar (optional, for better UX)

**GitHub:**
- `read:user`: Basic user profile
- `user:email`: Email address (required for account creation)

**Recommendation**: Only request scopes you actually need.

### Token Refresh

- **Automatic refresh**: Tokens are automatically refreshed when expired
- **Refresh token storage**: Securely encrypted in database
- **Token expiration**: Handled gracefully with re-authentication if refresh fails

### Redirect URI Validation

- **Strict matching**: OAuth providers validate exact redirect URI match
- **No wildcards**: Must specify exact URIs (no `*` allowed)
- **HTTPS required**: Production must use HTTPS redirect URIs

### Rate Limiting

- OAuth flows are subject to same rate limiting as password authentication
- Failed OAuth attempts count toward rate limit
- Account lockout applies after 5 failed attempts (any auth method)

---

## Advanced Configuration

### Custom OAuth Providers

To add additional OAuth providers (Microsoft, Apple, etc.):

1. Update `src/auth/oauth_handler.py`:
   - Add provider URLs and scopes
   - Update `OAuthHandler.__init__` to support new provider
   - Add profile standardization logic in `get_user_profile`

2. Update database schema:
   - Add provider to `auth_oauth_accounts.provider` CHECK constraint

3. Add environment variables:
   - `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, etc.

4. Update UI:
   - Add button in `render_oauth_buttons()` in `streamlit_auth.py`

### Token Refresh Automation

OAuth tokens are automatically refreshed when needed. To manually refresh:

```python
from src.auth.oauth_handler import OAuthHandler

# Get handler for provider
handler = await get_oauth_handler("google")

# Refresh tokens
new_token = await handler.refresh_access_token(refresh_token)
```

### Linking Multiple OAuth Accounts

Users can link multiple OAuth providers to the same account:

1. Log in with password or first OAuth provider
2. Navigate to user profile
3. Click "Link Google Account" or "Link GitHub Account"
4. Complete OAuth flow
5. OAuth account is linked to existing user

**Note**: This feature requires additional UI implementation (not included in v1.8.0).

---

## Migration Guide

### From YAML to Database Auth with OAuth

If you're already using YAML authentication and want to enable OAuth:

1. **Migrate existing users to database:**
   ```bash
   python -m src.auth.migrate_yaml_to_db
   ```

2. **Enable database auth:**
   ```bash
   # In .env
   USE_DATABASE_AUTH=true
   ```

3. **Set up OAuth as described above**

4. **Test both auth methods:**
   - Existing users can still log in with username/password
   - New users can sign up with Google/GitHub
   - OAuth users can be managed via CLI:
     ```bash
     python -m src.auth.db_cli list
     ```

### Rollback Plan

If you need to disable OAuth:

```bash
# In .env
OAUTH_ENABLED=false

# Restart app
make run-ui
```

Users created via OAuth can still log in (they exist in database), but OAuth login buttons won't appear.

To fully rollback to YAML:

```bash
# In .env
USE_DATABASE_AUTH=false
OAUTH_ENABLED=false

# Restart app
make run-ui
```

**Note**: OAuth users won't be able to log in with YAML backend (no password set).

---

## FAQ

**Q: Can I use OAuth without database authentication?**

A: No, OAuth requires `USE_DATABASE_AUTH=true`. OAuth users are stored in the database.

---

**Q: What happens if a user signs in with both Google and GitHub using the same email?**

A: The same user account is used. Multiple OAuth providers can be linked to one user account via the `auth_oauth_accounts` table.

---

**Q: How do I revoke OAuth access?**

A: Users can revoke access in their Google/GitHub account settings:
- Google: https://myaccount.google.com/permissions
- GitHub: https://github.com/settings/applications

The app will attempt to refresh tokens on next login. If refresh fails, user must re-authorize.

---

**Q: Can OAuth users change their password?**

A: OAuth-only users don't have a password. To enable password login for an OAuth user:

```bash
python -m src.auth.db_cli update-password --username oauth_user_123 --new-password "SecurePass123!"
```

This changes the user's `auth_method` to "hybrid" (both password and OAuth).

---

**Q: Is two-factor authentication (2FA) supported?**

A: Not in v1.8.0. 2FA is planned for v2.0.0. However, if users enable 2FA on their Google/GitHub accounts, that protection applies to OAuth login.

---

## Support

For issues or questions:

1. Check logs: `make run-ui | grep "OAuth"`
2. Review this guide's troubleshooting section
3. Check GitHub issues: https://github.com/your-repo/base_agent/issues
4. Create new issue with logs and configuration (redact secrets!)

---

## References

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [GitHub OAuth Documentation](https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps)
- [Authlib Documentation](https://docs.authlib.org/)
- [Cryptography (Fernet) Documentation](https://cryptography.io/en/latest/fernet/)

---

**Last Updated**: 2025-10-24
**Version**: 1.8.0
