-- =====================================================
-- 2FA and Password History Schema - Advanced Security
-- =====================================================
-- Creates tables for 2FA/TOTP authentication and password history tracking
-- =====================================================

-- =====================================================
-- TABLE: auth_totp_secrets
-- =====================================================
-- Stores TOTP secrets for 2FA-enabled users

CREATE TABLE IF NOT EXISTS auth_totp_secrets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES auth_users(id) ON DELETE CASCADE,

    -- TOTP Secret (encrypted)
    secret_encrypted TEXT NOT NULL,

    -- 2FA Status
    is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    verified_at TIMESTAMPTZ,  -- When 2FA was first verified

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_ip TEXT,

    -- Backup settings
    backup_codes_generated_at TIMESTAMPTZ,
    backup_codes_count INTEGER DEFAULT 0
);

-- Indexes for auth_totp_secrets
CREATE INDEX IF NOT EXISTS idx_auth_totp_user ON auth_totp_secrets(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_totp_enabled ON auth_totp_secrets(is_enabled) WHERE is_enabled = TRUE;

-- =====================================================
-- TABLE: auth_backup_codes
-- =====================================================
-- Stores one-time backup codes for 2FA recovery

CREATE TABLE IF NOT EXISTS auth_backup_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,

    -- Backup Code (hashed with bcrypt)
    code_hash TEXT NOT NULL,

    -- Usage Tracking
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    used_at TIMESTAMPTZ,
    used_ip TEXT,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ  -- Optional expiration (e.g., 90 days)
);

-- Indexes for auth_backup_codes
CREATE INDEX IF NOT EXISTS idx_auth_backup_user ON auth_backup_codes(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_auth_backup_unused ON auth_backup_codes(user_id, is_used) WHERE is_used = FALSE;

-- =====================================================
-- TABLE: auth_password_history
-- =====================================================
-- Tracks password history to prevent reuse

CREATE TABLE IF NOT EXISTS auth_password_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,

    -- Password Hash (bcrypt)
    password_hash TEXT NOT NULL,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_ip TEXT
);

-- Indexes for auth_password_history
CREATE INDEX IF NOT EXISTS idx_auth_pwd_history_user ON auth_password_history(user_id, created_at DESC);

-- =====================================================
-- TABLE: auth_2fa_attempts
-- =====================================================
-- Tracks 2FA verification attempts for rate limiting

CREATE TABLE IF NOT EXISTS auth_2fa_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,

    -- Attempt Details
    success BOOLEAN NOT NULL,
    code_type TEXT NOT NULL,  -- 'totp' or 'backup'

    -- Metadata
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address TEXT,
    user_agent TEXT
);

-- Indexes for auth_2fa_attempts
CREATE INDEX IF NOT EXISTS idx_auth_2fa_attempts_user ON auth_2fa_attempts(user_id, attempted_at DESC);
CREATE INDEX IF NOT EXISTS idx_auth_2fa_attempts_time ON auth_2fa_attempts(attempted_at);

-- =====================================================
-- TABLE: auth_captcha_challenges
-- =====================================================
-- Tracks CAPTCHA challenges and responses

CREATE TABLE IF NOT EXISTS auth_captcha_challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Challenge Details
    challenge_type TEXT NOT NULL,  -- 'hcaptcha', 'recaptcha', etc.
    username TEXT,  -- Optional, may be NULL for failed logins

    -- Response Tracking
    success BOOLEAN NOT NULL,
    response_time_ms INTEGER,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address TEXT,
    user_agent TEXT
);

-- Indexes for auth_captcha_challenges
CREATE INDEX IF NOT EXISTS idx_auth_captcha_username ON auth_captcha_challenges(username, created_at DESC) WHERE username IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_auth_captcha_ip ON auth_captcha_challenges(ip_address, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_auth_captcha_time ON auth_captcha_challenges(created_at);

-- =====================================================
-- TABLE: auth_breach_checks
-- =====================================================
-- Tracks haveibeenpwned.com API checks

CREATE TABLE IF NOT EXISTS auth_breach_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth_users(id) ON DELETE CASCADE,

    -- Check Details
    password_hash_prefix TEXT NOT NULL,  -- k-Anonymity: first 5 chars of SHA-1 hash
    is_breached BOOLEAN NOT NULL,
    breach_count INTEGER DEFAULT 0,  -- Number of times password appears in breaches

    -- Metadata
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    check_type TEXT NOT NULL,  -- 'registration', 'login', 'password_change', 'scheduled'
    ip_address TEXT
);

-- Indexes for auth_breach_checks
CREATE INDEX IF NOT EXISTS idx_auth_breach_user ON auth_breach_checks(user_id, checked_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_auth_breach_time ON auth_breach_checks(checked_at);

-- =====================================================
-- UPDATED COLUMNS FOR auth_users
-- =====================================================
-- Add columns to existing auth_users table for 2FA and security features

-- Add 2FA enforcement flag (for admin users)
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS requires_2fa BOOLEAN DEFAULT FALSE;

-- Add last password change tracking
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ DEFAULT NOW();

-- Add last breach check timestamp
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS last_breach_check_at TIMESTAMPTZ;

-- Create index for 2FA requirement
CREATE INDEX IF NOT EXISTS idx_auth_users_requires_2fa ON auth_users(requires_2fa) WHERE requires_2fa = TRUE;

-- =====================================================
-- RPC FUNCTIONS
-- =====================================================

-- Function to cleanup old password history (keep last 5 per user)
CREATE OR REPLACE FUNCTION cleanup_old_password_history()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH ranked_passwords AS (
        SELECT id,
               ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) as rn
        FROM auth_password_history
    )
    DELETE FROM auth_password_history
    WHERE id IN (
        SELECT id FROM ranked_passwords WHERE rn > 5
    );

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old 2FA attempts (keep last 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_2fa_attempts()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM auth_2fa_attempts
    WHERE attempted_at < NOW() - INTERVAL '30 days';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old CAPTCHA challenges (keep last 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_captcha_challenges()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM auth_captcha_challenges
    WHERE created_at < NOW() - INTERVAL '30 days';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old breach checks (keep last 90 days)
CREATE OR REPLACE FUNCTION cleanup_old_breach_checks()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM auth_breach_checks
    WHERE checked_at < NOW() - INTERVAL '90 days';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get unused backup codes count for user
CREATE OR REPLACE FUNCTION get_unused_backup_codes_count(p_user_id UUID)
RETURNS INTEGER AS $$
DECLARE
    code_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO code_count
    FROM auth_backup_codes
    WHERE user_id = p_user_id
    AND is_used = FALSE
    AND (expires_at IS NULL OR expires_at > NOW());

    RETURN COALESCE(code_count, 0);
END;
$$ LANGUAGE plpgsql;

-- Function to check if password was used recently (last 5 passwords)
CREATE OR REPLACE FUNCTION is_password_recently_used(p_user_id UUID, p_password_hash TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM (
            SELECT password_hash
            FROM auth_password_history
            WHERE user_id = p_user_id
            ORDER BY created_at DESC
            LIMIT 5
        ) recent_passwords
        WHERE password_hash = p_password_hash
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get 2FA status for user
CREATE OR REPLACE FUNCTION get_2fa_status(p_user_id UUID)
RETURNS TABLE(
    is_enabled BOOLEAN,
    verified_at TIMESTAMPTZ,
    backup_codes_count INTEGER,
    requires_2fa BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(t.is_enabled, FALSE) as is_enabled,
        t.verified_at,
        get_unused_backup_codes_count(p_user_id) as backup_codes_count,
        COALESCE(u.requires_2fa, FALSE) as requires_2fa
    FROM auth_users u
    LEFT JOIN auth_totp_secrets t ON t.user_id = u.id
    WHERE u.id = p_user_id
    AND u.deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql;

-- Function to count failed 2FA attempts in last hour
CREATE OR REPLACE FUNCTION count_recent_2fa_failures(p_user_id UUID)
RETURNS INTEGER AS $$
DECLARE
    failure_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO failure_count
    FROM auth_2fa_attempts
    WHERE user_id = p_user_id
    AND success = FALSE
    AND attempted_at > NOW() - INTERVAL '1 hour';

    RETURN COALESCE(failure_count, 0);
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE auth_totp_secrets IS 'Stores encrypted TOTP secrets for 2FA-enabled users';
COMMENT ON TABLE auth_backup_codes IS 'One-time backup codes for 2FA recovery (hashed with bcrypt)';
COMMENT ON TABLE auth_password_history IS 'Tracks last 5 password hashes to prevent reuse';
COMMENT ON TABLE auth_2fa_attempts IS 'Tracks 2FA verification attempts for rate limiting';
COMMENT ON TABLE auth_captcha_challenges IS 'Tracks CAPTCHA challenges and responses for security';
COMMENT ON TABLE auth_breach_checks IS 'Tracks haveibeenpwned.com breach detection checks';

COMMENT ON FUNCTION cleanup_old_password_history() IS 'Cleanup function: Keep only last 5 passwords per user';
COMMENT ON FUNCTION cleanup_old_2fa_attempts() IS 'Cleanup function: Remove 2FA attempts older than 30 days';
COMMENT ON FUNCTION cleanup_old_captcha_challenges() IS 'Cleanup function: Remove CAPTCHA challenges older than 30 days';
COMMENT ON FUNCTION cleanup_old_breach_checks() IS 'Cleanup function: Remove breach checks older than 90 days';
COMMENT ON FUNCTION get_unused_backup_codes_count(UUID) IS 'Get count of unused, non-expired backup codes for user';
COMMENT ON FUNCTION is_password_recently_used(UUID, TEXT) IS 'Check if password hash matches any of last 5 passwords';
COMMENT ON FUNCTION get_2fa_status(UUID) IS 'Get comprehensive 2FA status for user';
COMMENT ON FUNCTION count_recent_2fa_failures(UUID) IS 'Count failed 2FA attempts in last hour for rate limiting';
