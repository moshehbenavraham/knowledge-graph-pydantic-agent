# Authentication System - TODO

**Status**: ✅ v1.9.0 Complete | 🎯 Next: v2.0.0 Advanced Security Features

---

## 🟡 High Priority

### Database Migration & Deployment (v1.9.0)
**Time**: 30 minutes

- [ ] Apply database migration 006_email_verification.sql to production
- [ ] Test email verification flow end-to-end
- [ ] Verify password strength meter in all locations
- [ ] Test remember me checkbox functionality

---

## 🟢 Low Priority

### Advanced Security Features (v2.0.0)
**Time**: 3-4 hours

- [ ] 2FA/TOTP support (`pyotp` library)
  - QR code generation for authenticator apps
  - Backup codes generation
  - 2FA enforcement for admin users
- [ ] CAPTCHA after failed login attempts
- [ ] Password history (prevent reuse of last 5 passwords)
- [ ] Integration with haveibeenpwned.com for breach detection

### Additional OAuth Providers (v2.0.0)
**Time**: 2-3 hours

- [ ] Microsoft OAuth integration
- [ ] Apple OAuth integration
- [ ] UI for linking/unlinking OAuth accounts in user profile
- [ ] OAuth session analytics dashboard

---

**Last Updated**: 2025-10-25
