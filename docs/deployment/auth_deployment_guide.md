# Two-Layer Authentication Deployment Guide

## Overview

Base Agent uses a **two-layer authentication system** for maximum security:

1. **Layer 1 (ngrok)**: Basic HTTP Authentication at the network layer
2. **Layer 2 (Streamlit)**: User account authentication with session management

This provides defense-in-depth: even if one layer is bypassed, the other still protects the application.

## Architecture

```
Internet → ngrok (Basic Auth) → Streamlit (streamlit-authenticator) → Base Agent App
```

## Quick Start

### 1. Layer 1: ngrok Authentication (COMPLETED ✅)

**Status**: Already configured in `~/.config/ngrok/ngrok.yml`

**Credentials**:
- Username: `admin`
- Password: `BaseAgent2025!Secure`

**Test**:
```bash
# Without auth (should fail with 401)
curl https://aiwithapex.ngrok.io

# With auth (should succeed)
curl -u admin:BaseAgent2025!Secure https://aiwithapex.ngrok.io
```

### 2. Layer 2: Streamlit Authentication (COMPLETED ✅)

**Status**: Integrated into `src/ui/streamlit_app.py`

**Credentials**:
- Username: `admin`
- Password: `Admin2025!Secure`

**Configuration**: `config/auth_config.yaml` (never commit to git)

## User Management

### Create New User

```bash
python -m src.auth.user_manager create \
  --username john \
  --email john@example.com \
  --name "John Doe" \
  --password "SecurePassword123!"
```

### Update Password

```bash
python -m src.auth.user_manager update-password \
  --username john \
  --password "NewPassword456!"
```

### List All Users

```bash
python -m src.auth.user_manager list
```

### Delete User

```bash
python -m src.auth.user_manager delete --username john
```

### Generate Password Hash

```bash
python -m src.auth.hash_password "YourPasswordHere"
```

## Deployment Steps

### Development (localhost)

```bash
# 1. Start Streamlit (no authentication needed for localhost)
make run-ui

# Access: http://localhost:8501 (bypasses ngrok auth layer)
```

### Production (remote access via ngrok)

```bash
# 1. Ensure ngrok is configured with basic auth
cat ~/.config/ngrok/ngrok.yml | grep basic_auth

# 2. Start deployment
make deploy-ngrok

# 3. Check status
make ngrok-status

# 4. Access the public URL
# Browser prompt: Enter ngrok credentials (admin / BaseAgent2025!Secure)
# Login page: Enter Streamlit credentials (admin / Admin2025!Secure)
```

## Security Best Practices

### 1. Configuration Security

- ✅ **NEVER** commit `config/auth_config.yaml` to git
- ✅ Added to `.gitignore` automatically
- ✅ Store production credentials in environment variables or secrets manager
- ✅ Rotate `cookie.key` monthly in production

### 2. Password Security

- ✅ Use strong passwords (12+ characters, mixed case, numbers, symbols)
- ✅ Bcrypt hashing with 12 rounds (configurable)
- ✅ Different passwords for ngrok and Streamlit layers
- ✅ Change default passwords in production

### 3. Session Security

- ✅ 30-day cookie expiry (configurable)
- ✅ Auto-logout after 30 minutes of inactivity
- ✅ HTTPS required for secure cookies (ngrok provides this)
- ✅ Session token rotation on logout

### 4. Rate Limiting (TODO)

Implement in code:
- Max 5 login attempts per 15 minutes
- Exponential backoff for repeated failures
- CAPTCHA after 3 failed attempts
- Log all failed attempts to analytics

## Configuration Reference

### config/auth_config.yaml

```yaml
cookie:
  name: "base_agent_auth_cookie"
  key: "CHANGE_THIS_IN_PRODUCTION"  # Generate random string
  expiry_days: 30
  secure: false  # Set to true in production (requires HTTPS)

credentials:
  usernames:
    admin:
      email: "admin@baseagent.local"
      name: "Administrator"
      password: "$2b$12$..."  # Bcrypt hash

config:
  auto_logout: true
  auto_logout_minutes: 30
  bcrypt_log_rounds: 12
  max_login_attempts: 5
  lockout_duration_minutes: 15
```

### ~/.config/ngrok/ngrok.yml

```yaml
version: "3"
agent:
    authtoken: YOUR_NGROK_TOKEN

tunnels:
    base-agent-ui:
        proto: http
        addr: 8501
        domain: aiwithapex.ngrok.io
        inspect: true
        basic_auth:
            - "admin:BaseAgent2025!Secure"
```

## Troubleshooting

### Issue: "Config file not found"

**Cause**: `config/auth_config.yaml` doesn't exist

**Fix**:
```bash
# Ensure config file exists
ls config/auth_config.yaml

# If missing, it may have been accidentally deleted
# Recreate from template or re-run setup
```

### Issue: "Username or password is incorrect"

**Cause**: Invalid credentials

**Fix**:
1. Verify username exists: `python -m src.auth.user_manager list`
2. Reset password: `python -m src.auth.user_manager update-password --username admin --password NewPassword123!`

### Issue: "401 Unauthorized" on ngrok URL

**Cause**: ngrok basic auth is active

**Fix**: Enter credentials when browser prompts:
- Username: `admin`
- Password: `BaseAgent2025!Secure`

### Issue: Session expires too quickly

**Cause**: Short expiry or inactivity timeout

**Fix**: Edit `config/auth_config.yaml`:
```yaml
cookie:
  expiry_days: 90  # Increase from 30

config:
  auto_logout_minutes: 120  # Increase from 30
```

### Issue: Can't access localhost

**Cause**: Authentication is required for all access

**Fix**: Authentication applies to both local and remote access. Use credentials.

## Rollback Plan

### Disable Layer 2 (Streamlit Auth)

```python
# In src/ui/streamlit_app.py, comment out authentication:
async def main():
    st.set_page_config(...)

    # # Require authentication (Layer 2)
    # user_name, authenticator = require_authentication()
    # logger.info("User authenticated, loading main app", user=user_name)
    # st.session_state.authenticator = authenticator

    initialize_session_state()
```

### Disable Layer 1 (ngrok Auth)

Edit `~/.config/ngrok/ngrok.yml`:
```yaml
tunnels:
    base-agent-ui:
        proto: http
        addr: 8501
        domain: aiwithapex.ngrok.io
        inspect: true
        # basic_auth:  # Comment out this section
        #     - "admin:BaseAgent2025!Secure"
```

Then restart ngrok: `make deploy-ngrok`

## Monitoring & Analytics

### Authentication Events Logged

- ✅ Successful logins (username, timestamp)
- ✅ Failed login attempts (username, timestamp)
- ✅ Logout events (username, session duration)
- ✅ Session expirations (username, reason)

### View Logs

```bash
# Check Streamlit logs for auth events
make run-ui | grep "authentication"

# Check ngrok access logs
make ngrok-logs | grep "401"
```

### Analytics Dashboard

Future: Add authentication metrics to GraphRAG Dashboard
- Login success/failure rates
- Active sessions count
- Failed attempt patterns
- User activity heatmap

## Production Hardening (TODO)

### High Priority

1. **Environment Variables**: Move credentials to `.env`
2. **HTTPS Enforcement**: Set `cookie.secure: true`
3. **IP Whitelisting**: Add `ip_restriction` to ngrok config
4. **2FA**: Integrate TOTP with `pyotp`
5. **Database Storage**: Migrate user data to Supabase

### Medium Priority

1. **OAuth Integration**: Add Google/GitHub login
2. **Password Reset**: Email-based password recovery
3. **Session Management UI**: View/revoke active sessions
4. **Audit Logging**: Comprehensive auth event logging
5. **CAPTCHA**: Add after failed attempts

### Low Priority

1. **SSO**: Enterprise SSO integration (SAML/OIDC)
2. **Role-Based Access**: User roles and permissions
3. **Password Policy**: Enforce complexity requirements
4. **Account Lockout**: Automatic lockout after threshold
5. **Security Questions**: Additional authentication factors

## Testing Checklist

### Manual Testing

- [ ] Login with correct credentials
- [ ] Login with incorrect credentials (should fail)
- [ ] Logout and re-login
- [ ] Session persistence across page refreshes
- [ ] Auto-logout after inactivity
- [ ] ngrok basic auth prompt appears
- [ ] Create new user via CLI
- [ ] Update password via CLI
- [ ] Delete user via CLI

### Automated Testing

```bash
# Run auth tests (TODO: implement)
pytest tests/test_auth.py -v

# Run integration tests
pytest tests/test_auth_integration.py -v

# Run E2E tests
pytest tests/test_auth_e2e.py -v
```

## Next Steps

1. ✅ **Phase 2.1-2.3**: Basic authentication (COMPLETED)
2. ⏳ **Phase 2.4**: OAuth integration (Google, GitHub)
3. ⏳ **Phase 2.5**: Enhanced UI/UX (password reset, profile page)
4. ⏳ **Phase 2.6**: Security hardening (rate limiting, 2FA)
5. ⏳ **Phase 2.7**: Database integration (Supabase user management)
6. ⏳ **Phase 2.8**: Comprehensive testing and deployment

## Support

**Questions?** Check the main documentation:
- `README.md` - Project overview
- `CLAUDE.md` - Development guidelines
- `docs/analytics_system.md` - Analytics integration

**Issues?** Report at: https://github.com/anthropics/claude-code/issues

---

**Last Updated**: 2025-10-24
**Version**: v1.4.0 (two-layer authentication)
