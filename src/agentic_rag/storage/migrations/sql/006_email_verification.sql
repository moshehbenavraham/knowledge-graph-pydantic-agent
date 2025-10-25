-- =====================================================
-- Email Verification Schema - User Email Verification
-- =====================================================
-- Creates email verification token table for new user registration flow
-- =====================================================

-- =====================================================
-- TABLE: auth_email_verification_tokens
-- =====================================================
-- Temporary tokens for email verification flow

CREATE TABLE IF NOT EXISTS auth_email_verification_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,

    -- Token (REQUIRED - NOT NULL)
    token TEXT NOT NULL UNIQUE,
    token_hash TEXT NOT NULL,  -- bcrypt hash for verification

    -- Token Lifecycle (REQUIRED - NOT NULL)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,  -- Typically 24 hours
    verified_at TIMESTAMPTZ,  -- NULL if not verified, set when verification succeeds

    -- Security Metadata
    created_ip TEXT,
    verified_ip TEXT
);

-- Indexes for auth_email_verification_tokens
CREATE INDEX IF NOT EXISTS idx_auth_verify_tokens_user ON auth_email_verification_tokens(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_auth_verify_tokens_token ON auth_email_verification_tokens(token)
    WHERE verified_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_auth_verify_tokens_expires ON auth_email_verification_tokens(expires_at);

-- =====================================================
-- RPC FUNCTIONS
-- =====================================================

-- Function to cleanup expired verification tokens
CREATE OR REPLACE FUNCTION cleanup_expired_verification_tokens()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM auth_email_verification_tokens
    WHERE expires_at < NOW() - INTERVAL '7 days';  -- Keep for 7 days after expiry for audit

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to check if user has unverified email
CREATE OR REPLACE FUNCTION has_unverified_email(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM auth_users
        WHERE id = p_user_id
        AND is_email_verified = FALSE
        AND deleted_at IS NULL
    );
END;
$$ LANGUAGE plpgsql;
