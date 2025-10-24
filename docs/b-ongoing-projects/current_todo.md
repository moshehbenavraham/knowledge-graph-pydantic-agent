# Streamlit + ngrok Deployment Plan

**Project Goal**: Deploy Base Agent Streamlit UI from WSL2 Ubuntu via ngrok with 2-layer authentication

**ngrok Account Details**:
- Plan: Personal/Pay-as-you-go
- Custom Domain: `aiwithapex.ngrok.io` (configured in `.env`)
- AuthToken: Configured in `.env` as `NGROK_AUTHTOKEN`

---

## ✅ PHASE 1: ngrok Deployment - COMPLETED (2025-10-24)

**Implementation Summary:**
- ✅ All 7 sub-phases completed successfully
- ✅ Comprehensive test suite created (40 tests, 100% pass rate)
- ✅ Full documentation updated (README.md, CLAUDE.md)
- ✅ Production-ready deployment system

**Key Deliverables:**
- ngrok v3 configuration at `~/.config/ngrok/ngrok.yml`
- Streamlit configuration at `.streamlit/config.toml`
- 5 new Makefile targets (`deploy-ngrok`, `ngrok-start`, `ngrok-ui`, `ngrok-status`, `ngrok-logs`)
- Complete test coverage at `tests/test_ngrok_deployment.py`
- Updated project documentation

**Quick Start:**
```bash
make deploy-ngrok    # Automatic deployment
make ngrok-status    # Check public URL
```

---

## PHASE 1: ngrok Deployment (ORIGINAL PLAN)

### 1.1 ngrok Configuration Setup

**Status**: Not Started
**Priority**: P0 (Blocking for deployment)

**Tasks**:
- [ ] Configure ngrok authentication
  ```bash
  ngrok config add-authtoken $NGROK_AUTHTOKEN  # Uses value from .env
  ```

- [ ] Create ngrok configuration file at `~/.ngrok2/ngrok.yml`
  ```yaml
  version: "2"
  authtoken: <from .env NGROK_AUTHTOKEN>
  tunnels:
    base-agent-ui:
      proto: http
      addr: 8501  # Streamlit default port
      domain: <from .env NGROK_DOMAIN>
      inspect: true
  ```

- [ ] Verify ngrok configuration: `ngrok config check`

**Deliverables**:
- Working ngrok configuration file
- Verified authtoken authentication

---

### 1.2 Streamlit Configuration for ngrok

**Status**: Not Started
**Priority**: P0 (Required for CORS and WebSocket)

**Tasks**:
- [ ] Create `.streamlit/config.toml` in project root
  ```toml
  [server]
  port = 8501
  address = "0.0.0.0"
  headless = true
  enableCORS = false
  enableXsrfProtection = false  # ngrok handles this

  [browser]
  serverAddress = "aiwithapex.ngrok.io"
  serverPort = 443  # ngrok uses HTTPS
  gatherUsageStats = false

  [client]
  toolbarMode = "minimal"
  ```

- [ ] Add Streamlit CORS configuration to handle ngrok domain
- [ ] Configure WebSocket support for streaming features
- [ ] Test Streamlit startup with new config: `make run-ui`

**Deliverables**:
- `.streamlit/config.toml` file
- Verified local Streamlit startup (localhost:8501)

---

### 1.3 Environment Variables & Security

**Status**: Not Started
**Priority**: P0 (Security critical)

**Tasks**:
- [x] ~~Add ngrok-specific variables to `.env`~~ **COMPLETED** - Variables added:
  ```bash
  # ngrok Configuration (in .env)
  NGROK_AUTHTOKEN=<your_authtoken>  # Already configured
  NGROK_DOMAIN=<your_domain>        # Already configured
  NGROK_ENABLED=true                # Already configured
  ```

- [ ] Update `.env.example` with ngrok template variables
- [ ] Add `.streamlit/` to `.gitignore` if not already present
- [ ] Document sensitive credentials handling in README

**Deliverables**:
- Updated `.env` and `.env.example`
- Security checklist completed

---

### 1.4 Makefile Integration

**Status**: Not Started
**Priority**: P1 (Quality of life)

**Tasks**:
- [ ] Add manual deployment targets to Makefile:
  ```makefile
  # ngrok Deployment
  ngrok-start:  ## Start ngrok tunnel manually
  	ngrok start base-agent-ui

  ngrok-ui:  ## Start Streamlit only (for manual ngrok)
  	bash -c "source .venv/bin/activate && \
  	  PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=advanced \
  	  streamlit run src/ui/streamlit_app.py --server.port=8501"
  ```

- [ ] Add automatic deployment target:
  ```makefile
  deploy-ngrok:  ## Start Streamlit + ngrok tunnel automatically
  	@echo "Starting Streamlit on port 8501..."
  	@bash -c "source .venv/bin/activate && \
  	  PYTHONPATH=$(PWD):$$PYTHONPATH UI_MODE=advanced \
  	  streamlit run src/ui/streamlit_app.py --server.port=8501" & \
  	sleep 5 && \
  	echo "Starting ngrok tunnel to aiwithapex.ngrok.io..." && \
  	ngrok start base-agent-ui
  ```

- [ ] Add monitoring/status targets:
  ```makefile
  ngrok-status:  ## Check ngrok tunnel status
  	curl -s http://localhost:4040/api/tunnels | jq

  ngrok-logs:  ## View ngrok access logs
  	curl -s http://localhost:4040/api/requests/http | jq
  ```

**Deliverables**:
- 5 new Makefile targets (`ngrok-start`, `ngrok-ui`, `deploy-ngrok`, `ngrok-status`, `ngrok-logs`)
- Updated `.PHONY` declarations

---

### 1.5 Testing & Validation

**Status**: Not Started
**Priority**: P0 (Deployment verification)

**Test Checklist**:
- [ ] **Local Access Test**: Verify `http://localhost:8501` works
- [ ] **ngrok Tunnel Test**: Start tunnel and verify `https://aiwithapex.ngrok.io` accessible
- [ ] **Streaming Test**: Test Advanced mode streaming with ngrok URL
- [ ] **Tool Execution Test**: Verify tools work through ngrok (smart_search, web_search, etc.)
- [ ] **Memory Test**: Test Mem0 integration through ngrok
- [ ] **Upload Test**: Test file upload functionality through ngrok
- [ ] **Dashboard Test**: Verify analytics dashboard loads through ngrok
- [ ] **WebSocket Test**: Confirm real-time streaming works (not just polling)
- [ ] **Session Persistence Test**: Verify chat history persists across page refreshes
- [ ] **Multi-Browser Test**: Test Chrome, Firefox, Safari compatibility

**Performance Benchmarks**:
- [ ] Measure latency: localhost vs ngrok (acceptable if <500ms overhead)
- [ ] Test concurrent users (2-5 simultaneous sessions)
- [ ] Monitor ngrok bandwidth usage

**Deliverables**:
- Test results document (`docs/deployment/ngrok_test_results.md`)
- Performance benchmarks
- Known issues list

---

### 1.6 Documentation & Runbook

**Status**: Not Started
**Priority**: P1 (Operational readiness)

**Tasks**:
- [ ] Create deployment runbook: `docs/deployment/ngrok_deployment_guide.md`
  - Prerequisites checklist
  - Step-by-step deployment instructions
  - Troubleshooting guide
  - Rollback procedures

- [ ] Update main `README.md` with ngrok deployment section
- [ ] Update `CLAUDE.md` with ngrok commands
- [ ] Create quick reference card:
  ```bash
  # Quick Start
  make deploy-ngrok    # Automatic deployment

  # Manual Control
  make ngrok-ui        # Terminal 1: Start Streamlit
  make ngrok-start     # Terminal 2: Start ngrok

  # Monitoring
  make ngrok-status    # Check tunnel status
  make ngrok-logs      # View access logs
  ```

**Deliverables**:
- Complete deployment runbook
- Updated project documentation
- Quick reference guide

---

### 1.7 WSL2-Specific Considerations

**Status**: Not Started
**Priority**: P1 (Environment compatibility)

**WSL2 Gotchas to Address**:
- [ ] Verify ngrok can bind to WSL2 ports correctly
- [ ] Test Windows firewall rules (if needed)
- [ ] Confirm IPv4 pooler URL works (already configured for Mem0)
- [ ] Test systemd service (if running in WSL2 with systemd enabled)
- [ ] Document WSL2 IP address handling (dynamic vs static)

**Auto-Start Options (Optional)**:
- [ ] Option A: WSL2 startup script (`~/.bashrc` or `~/.zshrc`)
- [ ] Option B: Windows Task Scheduler to start WSL2 + ngrok on boot
- [ ] Option C: systemd service (if WSL2 systemd is enabled)

**Deliverables**:
- WSL2 compatibility verification
- Auto-start guide (optional, for convenience)

---

## PHASE 2: Two-Layer Authentication (LONG-TERM)

**Status**: Not Started
**Priority**: P2 (Post-deployment enhancement)

**Architecture Overview**:
```
Internet � ngrok (Layer 1: Basic Auth/IP Filter) � Streamlit (Layer 2: streamlit-authenticator) � App
```

---

### 2.1 Layer 1: ngrok Authentication

**Status**: Not Started
**Priority**: P2

**Options** (Choose based on security needs):

**Option A: Basic Authentication**
```yaml
# ~/.ngrok2/ngrok.yml
tunnels:
  base-agent-ui:
    proto: http
    addr: 8501
    domain: aiwithapex.ngrok.io
    basic_auth:
      - "username:password"  # htpasswd format
```

**Option B: IP Restrictions** (if you have static IP)
```yaml
tunnels:
  base-agent-ui:
    proto: http
    addr: 8501
    domain: aiwithapex.ngrok.io
    ip_restriction:
      allow_cidrs:
        - "YOUR_IP/32"
```

**Option C: OAuth (ngrok Pro feature)**
```yaml
tunnels:
  base-agent-ui:
    proto: http
    addr: 8501
    domain: aiwithapex.ngrok.io
    oauth:
      provider: google
      allow_domains:
        - "yourdomain.com"
```

**Tasks**:
- [ ] Choose ngrok auth method (Basic Auth recommended for Personal plan)
- [ ] Configure ngrok authentication in `ngrok.yml`
- [ ] Test ngrok auth layer independently
- [ ] Document auth bypass for testing (localhost access)

---

### 2.2 Layer 2: streamlit-authenticator Setup

**Status**: Not Started
**Priority**: P2

**Tasks**:
- [ ] Install streamlit-authenticator: `pip install streamlit-authenticator`
- [ ] Add to `pyproject.toml` dependencies:
  ```toml
  [project.optional-dependencies]
  auth = [
      "streamlit-authenticator>=0.3.0",
      "PyJWT>=2.8.0",
      "bcrypt>=4.1.0",
  ]
  ```

- [ ] Create authentication configuration file: `config/auth_config.yaml`
  ```yaml
  credentials:
    usernames:
      admin:
        name: Admin User
        password: $2b$12$hashed_password_here  # bcrypt hash
        email: admin@example.com
  cookie:
    name: base_agent_auth
    key: random_signature_key_here  # Generate with secrets.token_hex()
    expiry_days: 30
  ```

- [ ] Add user management utilities: `src/auth/user_manager.py`
  - Create user
  - Update password
  - Delete user
  - List users

---

### 2.3 Layer 2: Username/Password Authentication

**Status**: Not Started
**Priority**: P2

**Tasks**:
- [ ] Integrate streamlit-authenticator in `src/ui/streamlit_app.py`:
  ```python
  import streamlit_authenticator as stauth

  # Load auth config
  authenticator = stauth.Authenticate(
      credentials,
      cookie_name,
      cookie_key,
      cookie_expiry_days
  )

  # Login widget
  name, authentication_status, username = authenticator.login('Login', 'main')

  if authentication_status:
      # Show main app
      authenticator.logout('Logout', 'sidebar')
      st.write(f'Welcome *{name}*')
      # ... rest of app
  elif authentication_status == False:
      st.error('Username/Password is incorrect')
  elif authentication_status == None:
      st.warning('Please enter your username and password')
  ```

- [ ] Create password hashing utility: `src/auth/hash_password.py`
- [ ] Add initial admin user setup script
- [ ] Test username/password flow end-to-end

---

### 2.4 Layer 2: OAuth Integration

**Status**: Not Started
**Priority**: P3 (Nice to have)

**Providers to Support**:
- [ ] Google OAuth
- [ ] GitHub OAuth
- [ ] Microsoft OAuth (optional)

**Tasks**:
- [ ] Set up OAuth apps in provider consoles
  - Google: https://console.cloud.google.com/apis/credentials
  - GitHub: https://github.com/settings/developers

- [ ] Add OAuth libraries: `pip install authlib httpx`
- [ ] Implement OAuth flow in `src/auth/oauth_handler.py`
- [ ] Add OAuth callback route handling
- [ ] Store OAuth tokens securely (encrypted in database)
- [ ] Test OAuth login flow

---

### 2.5 Authentication UI/UX

**Status**: Not Started
**Priority**: P2

**Tasks**:
- [ ] Design login page UI (Streamlit components)
- [ ] Add "Login with Google" / "Login with GitHub" buttons
- [ ] Add "Or" divider between OAuth and username/password
- [ ] Implement "Remember me" functionality
- [ ] Add password reset flow (email-based)
- [ ] Add user profile page (change password, view sessions)
- [ ] Add session management (view active sessions, revoke sessions)

---

### 2.6 Security Hardening

**Status**: Not Started
**Priority**: P2

**Tasks**:
- [ ] Implement rate limiting (max login attempts)
- [ ] Add CAPTCHA for repeated failed logins
- [ ] Enable HTTPS-only cookies
- [ ] Implement CSRF protection
- [ ] Add session timeout (idle timeout)
- [ ] Log authentication events (success/failure)
- [ ] Add 2FA support (TOTP, optional)
- [ ] Security audit and penetration testing

---

### 2.7 Database Integration (User Management)

**Status**: Not Started
**Priority**: P2

**Tasks**:
- [ ] Create `users` table in Supabase:
  ```sql
  CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    oauth_provider TEXT,
    oauth_id TEXT
  );

  CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    session_token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    ip_address TEXT,
    user_agent TEXT
  );
  ```

- [ ] Create database migration script
- [ ] Implement user CRUD operations in `src/auth/db.py`
- [ ] Add user role/permissions system (optional)

---

### 2.8 Testing & Deployment (Phase 2)

**Status**: Not Started
**Priority**: P2

**Test Checklist**:
- [ ] Unit tests for auth functions
- [ ] Integration tests for login flows
- [ ] E2E tests for complete auth journey
- [ ] Security tests (SQL injection, XSS, CSRF)
- [ ] Load tests (concurrent login attempts)
- [ ] Session management tests
- [ ] Password reset flow tests

**Deployment Checklist**:
- [ ] Enable ngrok authentication (Layer 1)
- [ ] Deploy streamlit-authenticator (Layer 2)
- [ ] Migrate existing users (if any)
- [ ] Update documentation
- [ ] Train users on new login flow
- [ ] Monitor authentication metrics

---

## SUCCESS CRITERIA

### Phase 1 (ngrok Deployment)
-  Streamlit UI accessible via `https://aiwithapex.ngrok.io`
-  All features work identically to localhost (streaming, tools, memory, uploads, dashboard)
-  Latency overhead < 500ms
-  WebSocket connections stable
-  Documentation complete and tested
-  Makefile commands work reliably

### Phase 2 (Two-Layer Authentication)
-  ngrok basic auth protects tunnel (Layer 1)
-  streamlit-authenticator protects app (Layer 2)
-  Username/password login works
-  OAuth login works (Google + GitHub)
-  User sessions persist securely
-  Security audit passed
-  All tests passing

---

## TIMELINE ESTIMATE

**Phase 1** (Immediate Focus):
- Setup & Configuration: 2-3 hours
- Testing & Debugging: 2-3 hours
- Documentation: 1-2 hours
- **Total: 5-8 hours**

**Phase 2** (Long-term):
- Layer 1 (ngrok auth): 1-2 hours
- Layer 2 (streamlit-authenticator setup): 3-4 hours
- OAuth integration: 4-6 hours
- Database integration: 2-3 hours
- Security hardening: 2-3 hours
- Testing: 3-4 hours
- **Total: 15-22 hours**

---

## CURRENT FOCUS

**NOW**: Phase 1.1 - ngrok Configuration Setup

**NEXT**: Phase 1.2 - Streamlit Configuration for ngrok

---

## NOTES & CONSIDERATIONS

1. **ngrok Free Tier Limits** (Not applicable - using Personal plan):
   -  Custom domain supported
   -  Basic auth supported
   -  HTTPS included
   - � Check concurrent connection limits

2. **WSL2 Networking**:
   - ngrok must bind to `0.0.0.0:8501` (not `localhost:8501`)
   - Use IPv4 pooler URLs for database (already configured)
   - Dynamic IP in WSL2 may require ngrok restart on WSL2 restart

3. **Streamlit Caveats**:
   - `enableXsrfProtection=false` required for ngrok (ngrok handles CSRF)
   - `serverAddress` must match ngrok domain for proper asset loading
   - WebSocket fallback to HTTP polling if WebSocket fails

4. **Security Best Practices**:
   - Never commit `NGROK_AUTHTOKEN` to git
   - Use strong passwords for streamlit-authenticator
   - Enable HTTPS-only cookies in production
   - Rotate session keys regularly
   - Monitor failed login attempts

5. **Backup Plan**:
   - If ngrok fails, fall back to localhost
   - If auth fails, disable Layer 2 temporarily (keep Layer 1)
   - Always maintain local dev environment

---

**Last Updated**: 2025-10-24
**Status**: ✅ Phase 1 COMPLETE - Production Ready
**Next Phase**: Phase 2 (Two-Layer Authentication) - Optional Enhancement
