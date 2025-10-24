# Authentication System - TODO

**Status**: 🚧 In Progress (v1.7.0 - 87.4% complete)

---

## 🔴 High Priority

### Complete Test Suite (v1.7.0)
**Time**: 2-3 hours | **Tests**: 139/159 passing (20 remaining failures)

#### test_auth_db.py (14 failures remaining)
- [ ] Fix `list_users` not returning proper data structure from mock
- [ ] Fix `increment_failed_login` returning wrong count (expected 1, got 2; expected 5, got 6)
- [ ] Fix `get_session_expired` not filtering expired sessions
- [ ] Fix cleanup functions (`cleanup_expired_sessions`, `cleanup_reset_tokens`) returning mock objects instead of counts
- [ ] Fix `verify_reset_token_expired` invalid salt error
- [ ] Fix `use_reset_token_invalid` raising exception instead of returning False
- [ ] Fix `update_oauth_tokens` returning dict instead of boolean
- [ ] Fix `assign_role` returning dict instead of boolean
- [ ] Fix `get_user_roles` returning empty list
- [ ] Fix `check_permission_has_permission` returning False instead of True
- [ ] Fix `create_user_without_password` username assertion

#### test_password_reset.py (2 failures remaining)
- [ ] Fix SMTP `login()` method not being called in mock
- [ ] Fix authentication error test not detecting failed login

#### ✅ test_user_profile.py (COMPLETE - 0 failures)
- [x] Fixed import paths for `verify_user_password` and `update_user_password`
- [x] Added missing `mock_supabase_client` fixture
- [x] Corrected patch paths to `src.auth.db`

#### ✅ test_migrate_yaml_to_db.py (COMPLETE - 0 failures)
- [x] Fixed Supabase client mock with dynamic `table()` method
- [x] Resolved mock collision for existing user checks

#### ✅ test_db_cli.py (COMPLETE - 0 failures)
- [x] Fixed stdin mocking with `builtins.input`
- [x] All CLI commands working

---

## 🟡 Medium Priority

### OAuth Integration (v1.8.0)
**Time**: 4-6 hours

- [ ] Install dependencies: `authlib`, `httpx`
- [ ] Set up OAuth apps (Google Console, GitHub Settings)
- [ ] Build `src/auth/oauth_handler.py`
  - OAuth flow implementation (authorization, callback, token exchange)
  - Token storage (encrypted in Supabase `auth_oauth_accounts`)
  - Token refresh logic
- [ ] Add OAuth buttons to login UI
- [ ] Test complete OAuth flow (Google → GitHub → token refresh)

**Note**: Database infrastructure already exists (`auth_oauth_accounts` table)

---

### Enhanced UI/UX Features (v1.9.0)
**Time**: 2-3 hours

- [ ] Password strength meter (visual feedback during password entry)
- [ ] Profile pictures support (upload + display)
- [ ] "Remember me" checkbox (extended session duration)
- [ ] Email verification for new users
- [ ] Improved password reset email template

---

## 🟢 Low Priority

### Advanced Security Features (v2.0.0)
**Time**: 2-3 hours

- [ ] 2FA/TOTP support (`pyotp` library)
  - QR code generation for authenticator apps
  - Backup codes generation
  - 2FA enforcement for admin users
- [ ] CAPTCHA after failed login attempts
- [ ] Password history (prevent reuse of last 5 passwords)
- [ ] Email verification flow for new signups

---

**Last Updated**: 2025-10-24
