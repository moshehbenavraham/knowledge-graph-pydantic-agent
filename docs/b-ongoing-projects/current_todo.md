# Authentication System - TODO

**Status**: ✅ v1.7.0 Complete | 🎯 Next: v1.8.0 OAuth Integration

---

## 🟡 High Priority

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
