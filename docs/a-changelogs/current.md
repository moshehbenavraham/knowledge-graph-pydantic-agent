# Changelog

All notable changes to the Base Agent project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Previous changelogs**: See `/docs/a-changelogs/archive/` for historical changes

---
---

## [1.5.0] - 2025-10-24

### Added
- **Database-backed authentication system** with hybrid YAML/database backend toggle
  - 5 Supabase tables: `auth_users`, `auth_sessions`, `auth_password_reset_tokens`, `auth_oauth_accounts`, `auth_roles` + `auth_user_roles`
  - 36 async database functions in `src/auth/db.py` (users, sessions, tokens, OAuth, roles)
  - Environment variable `USE_DATABASE_AUTH` to toggle between YAML and database backends
  - Seamless backward compatibility with existing YAML authentication

- **Comprehensive user management CLI** (`src/auth/db_cli.py`)
  - 8 commands: create, list, get, update, update-password, delete, role, sessions
  - Support for soft delete with `deleted_at` timestamp
  - Role-based permissions system (admin, user, viewer)
  - Rich terminal output with formatting and confirmation prompts

- **YAML to database migration tool** (`src/auth/migrate_yaml_to_db.py`)
  - Automatic backup creation before migration
  - Dry-run mode for testing migration
  - Role assignment during migration (admin role for 'admin' user)
  - Preserves all existing users with bcrypt hashes

- **Password reset flow** (Database mode only)
  - Email-based token generation with 1-hour expiration
  - SMTP email sending (pluggable for SendGrid/Mailgun)
  - "Forgot Password?" UI in login page
  - Dedicated reset completion page accessible via `?token=...` query param
  - Password strength validation (8+ chars, mixed case, numbers, special chars)
  - Secure token storage with bcrypt hashing

- **User profile UI component** (`src/auth/user_profile.py`)
  - Database mode: Full profile with password change, active sessions viewer, session revocation
  - YAML mode: Simplified profile with account information only
  - Integrated into Streamlit sidebar
  - Change password with current password verification
  - View/revoke individual sessions or all sessions (logs out everywhere)

- **Comprehensive documentation**
  - Deployment guide: `docs/deployment/database_auth_deployment.md` (484 lines)
  - Quick start guide: `docs/deployment/QUICKSTART_DATABASE_AUTH.md` (195 lines)
  - Implementation summary: `docs/deployment/v1.5.0_implementation_summary.md` (467 lines)

### Changed
- **Updated `src/auth/streamlit_auth.py`** (+181 lines)
  - Added hybrid backend support with `USE_DATABASE_AUTH` flag
  - Added `load_credentials_from_database()` function
  - Modified `load_auth_config()` for hybrid backend
  - Added `create_db_session()` and `revoke_db_session()` functions
  - Modified `require_authentication()` for database session tracking
  - Modified `render_logout_button()` for database session revocation
  - Added password reset UI in login page (expander)

- **Updated `src/ui/streamlit_app.py`** (+30 lines)
  - Imported user profile rendering functions
  - Added password reset page routing (query param: `token`)
  - Integrated user profile into sidebar (database + YAML modes)
  - Conditional rendering based on `USE_DATABASE_AUTH`

### Security
- All passwords hashed with bcrypt (12 rounds)
- Password reset tokens hashed with bcrypt for additional security
- Secure token generation using `secrets.token_urlsafe()`
- IP tracking for login attempts, password resets, session creation
- Soft delete prevents permanent data loss
- Session expiration and revocation
- Password strength validation enforced

### Environment Variables
- `USE_DATABASE_AUTH`: Toggle between database (true) and YAML (false) backends
- `AUTH_COOKIE_KEY`: Secure random key for cookie signing
- `PASSWORD_RESET_URL`: Base URL for password reset completion page
- `EMAIL_ENABLED`: Enable/disable email sending
- `EMAIL_PROVIDER`: Email provider (smtp, sendgrid, mailgun)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`: SMTP configuration

### Deployment
- Production-ready with comprehensive deployment guide
- Zero-downtime rollback: Set `USE_DATABASE_AUTH=false`
- Migration script preserves all existing users with automatic backups
- Quick start in 5 steps (~10 minutes)

### Testing
- Existing 47 auth tests still passing (100% success rate)
- Security audit: Bandit scan passed (0 vulnerabilities)
- Database integration tests deferred to v1.6.0

### Statistics
- **Total new code**: 2,910 lines across 9 new files
- **Implementation time**: ~9 hours (vs 11-15 estimated)
- **Completion**: 9/10 core features (90%)
- **Files created**: 9 new files, 5 modified files

### Deferred to v1.6.0
- OAuth integration (Google, GitHub) - P3 priority
- Comprehensive automated tests for database features
- 2FA/TOTP support
- Enhanced UI/UX (password strength meter, profile pictures)





---
---

## Previous Versions

**Previous changelogs**: See `/docs/a-changelogs/archive/` for historical changes

---

## Version Numbering

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR** version (X.0.0) for incompatible API changes
- **MINOR** version (0.X.0) for new functionality in a backward compatible manner
- **PATCH** version (0.0.X) for backward compatible bug fixes
