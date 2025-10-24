-- =====================================================
-- Authentication Schema Migration - User Management & Security
-- =====================================================
-- Creates comprehensive authentication tables for:
-- - Username/password authentication
-- - OAuth integration (Google, GitHub)
-- - Password reset flows
-- - Session management
-- - User roles/permissions
-- =====================================================

-- =====================================================
-- TABLE: auth_users
-- =====================================================
-- Core user authentication and profile data

CREATE TABLE IF NOT EXISTS auth_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Authentication Credentials (REQUIRED - NOT NULL)
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT,  -- NULL for OAuth-only users

    -- Profile Information
    full_name TEXT NOT NULL,
    avatar_url TEXT,

    -- Account Status (REQUIRED - NOT NULL)
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    email_verified_at TIMESTAMPTZ,

    -- Security Tracking
    failed_login_attempts INTEGER NOT NULL DEFAULT 0 CHECK (failed_login_attempts >= 0),
    locked_until TIMESTAMPTZ,  -- NULL if not locked
    last_login_at TIMESTAMPTZ,
    last_login_ip TEXT,

    -- Authentication Method (REQUIRED - NOT NULL)
    auth_method TEXT NOT NULL DEFAULT 'password' CHECK (auth_method IN (
        'password', 'oauth', 'hybrid'  -- hybrid = both password and OAuth
    )),

    -- Timestamps (REQUIRED - NOT NULL)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ  -- Soft delete support
);

-- Indexes for auth_users
CREATE INDEX IF NOT EXISTS idx_auth_users_username ON auth_users(username) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_auth_users_email ON auth_users(email) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_auth_users_active ON auth_users(is_active, deleted_at);
CREATE INDEX IF NOT EXISTS idx_auth_users_created ON auth_users(created_at DESC);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_auth_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auth_users_updated_at
    BEFORE UPDATE ON auth_users
    FOR EACH ROW
    EXECUTE FUNCTION update_auth_users_updated_at();

-- =====================================================
-- TABLE: auth_sessions
-- =====================================================
-- Active user sessions with device tracking

CREATE TABLE IF NOT EXISTS auth_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,

    -- Session Token (REQUIRED - NOT NULL)
    session_token TEXT NOT NULL UNIQUE,

    -- Session Metadata
    device_info TEXT,
    user_agent TEXT,
    ip_address TEXT,

    -- Session Lifecycle (REQUIRED - NOT NULL)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,  -- Session expiration
    revoked_at TIMESTAMPTZ,  -- NULL if active, set when user logs out

    -- Session Type
    session_type TEXT NOT NULL DEFAULT 'web' CHECK (session_type IN (
        'web', 'api', 'mobile', 'desktop'
    ))
);

-- Indexes for auth_sessions
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_token ON auth_sessions(session_token) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires ON auth_sessions(expires_at) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_auth_sessions_active ON auth_sessions(user_id, last_activity_at DESC)
    WHERE revoked_at IS NULL AND expires_at > NOW();

-- =====================================================
-- TABLE: auth_password_reset_tokens
-- =====================================================
-- Temporary tokens for password reset flow

CREATE TABLE IF NOT EXISTS auth_password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,

    -- Token (REQUIRED - NOT NULL)
    token TEXT NOT NULL UNIQUE,
    token_hash TEXT NOT NULL,  -- bcrypt hash for verification

    -- Token Lifecycle (REQUIRED - NOT NULL)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,  -- Typically 1 hour
    used_at TIMESTAMPTZ,  -- NULL if not used, set when password reset succeeds

    -- Security Metadata
    created_ip TEXT,
    used_ip TEXT
);

-- Indexes for auth_password_reset_tokens
CREATE INDEX IF NOT EXISTS idx_auth_reset_tokens_user ON auth_password_reset_tokens(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_auth_reset_tokens_token ON auth_password_reset_tokens(token)
    WHERE used_at IS NULL AND expires_at > NOW();
CREATE INDEX IF NOT EXISTS idx_auth_reset_tokens_expires ON auth_password_reset_tokens(expires_at);

-- =====================================================
-- TABLE: auth_oauth_accounts
-- =====================================================
-- OAuth provider linkages (Google, GitHub, etc.)

CREATE TABLE IF NOT EXISTS auth_oauth_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,

    -- OAuth Provider (REQUIRED - NOT NULL)
    provider TEXT NOT NULL CHECK (provider IN (
        'google', 'github', 'microsoft', 'apple'
    )),
    provider_user_id TEXT NOT NULL,  -- User ID from OAuth provider

    -- OAuth Tokens (encrypted at application layer)
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,

    -- OAuth Profile Data (JSONB for flexibility)
    profile_data JSONB NOT NULL DEFAULT '{}',  -- email, name, avatar, etc.

    -- Account Status (REQUIRED - NOT NULL)
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Timestamps (REQUIRED - NOT NULL)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,

    -- Ensure one provider account per user
    CONSTRAINT unique_user_provider UNIQUE (user_id, provider),
    -- Ensure provider user IDs are unique per provider
    CONSTRAINT unique_provider_user UNIQUE (provider, provider_user_id)
);

-- Indexes for auth_oauth_accounts
CREATE INDEX IF NOT EXISTS idx_auth_oauth_user ON auth_oauth_accounts(user_id, provider);
CREATE INDEX IF NOT EXISTS idx_auth_oauth_provider ON auth_oauth_accounts(provider, provider_user_id);
CREATE INDEX IF NOT EXISTS idx_auth_oauth_active ON auth_oauth_accounts(is_active);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_auth_oauth_accounts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auth_oauth_accounts_updated_at
    BEFORE UPDATE ON auth_oauth_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_auth_oauth_accounts_updated_at();

-- =====================================================
-- TABLE: auth_roles
-- =====================================================
-- User roles for permissions management (optional, for future)

CREATE TABLE IF NOT EXISTS auth_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Role Details (REQUIRED - NOT NULL)
    role_name TEXT NOT NULL UNIQUE,
    description TEXT,

    -- Permissions (JSONB array of permission strings)
    permissions JSONB NOT NULL DEFAULT '[]',

    -- Role Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Default roles
INSERT INTO auth_roles (role_name, description, permissions) VALUES
    ('admin', 'Full system access', '["*"]'),
    ('user', 'Standard user access', '["read", "write_own", "delete_own"]'),
    ('viewer', 'Read-only access', '["read"]')
ON CONFLICT (role_name) DO NOTHING;

-- =====================================================
-- TABLE: auth_user_roles
-- =====================================================
-- Many-to-many relationship between users and roles

CREATE TABLE IF NOT EXISTS auth_user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES auth_roles(id) ON DELETE CASCADE,

    -- Assignment Metadata
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by UUID REFERENCES auth_users(id),  -- Who granted the role

    -- Ensure one role per user (can have multiple rows for multiple roles)
    CONSTRAINT unique_user_role UNIQUE (user_id, role_id)
);

-- Indexes for auth_user_roles
CREATE INDEX IF NOT EXISTS idx_auth_user_roles_user ON auth_user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_user_roles_role ON auth_user_roles(role_id);

-- =====================================================
-- MAINTENANCE FUNCTIONS
-- =====================================================

-- Function to clean up expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_auth_sessions() RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM auth_sessions
    WHERE expires_at < NOW()
    AND revoked_at IS NULL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up expired/used password reset tokens
CREATE OR REPLACE FUNCTION cleanup_auth_reset_tokens() RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM auth_password_reset_tokens
    WHERE (expires_at < NOW() OR used_at IS NOT NULL)
    AND created_at < NOW() - INTERVAL '7 days';  -- Keep for 7 days for audit

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to unlock accounts after lockout period
CREATE OR REPLACE FUNCTION unlock_expired_auth_lockouts() RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE auth_users
    SET failed_login_attempts = 0,
        locked_until = NULL
    WHERE locked_until IS NOT NULL
    AND locked_until < NOW();

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get user with roles (helper for application)
CREATE OR REPLACE FUNCTION get_user_with_roles(p_user_id UUID)
RETURNS TABLE (
    id UUID,
    username TEXT,
    email TEXT,
    full_name TEXT,
    is_active BOOLEAN,
    roles JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        u.id,
        u.username,
        u.email,
        u.full_name,
        u.is_active,
        COALESCE(
            jsonb_agg(
                jsonb_build_object(
                    'role_name', r.role_name,
                    'permissions', r.permissions
                )
            ) FILTER (WHERE r.id IS NOT NULL),
            '[]'::jsonb
        ) as roles
    FROM auth_users u
    LEFT JOIN auth_user_roles ur ON u.id = ur.user_id
    LEFT JOIN auth_roles r ON ur.role_id = r.id
    WHERE u.id = p_user_id
    AND u.deleted_at IS NULL
    GROUP BY u.id, u.username, u.email, u.full_name, u.is_active;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- SECURITY POLICIES (Row Level Security - Optional)
-- =====================================================
-- Uncomment if you want to enable RLS for additional security

-- ALTER TABLE auth_users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE auth_sessions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE auth_oauth_accounts ENABLE ROW LEVEL SECURITY;

-- Example policy: Users can only read their own data
-- CREATE POLICY users_read_own ON auth_users
--     FOR SELECT
--     USING (id = current_setting('app.current_user_id')::UUID);

-- =====================================================
-- GRANT PERMISSIONS (if using specific roles)
-- =====================================================
-- Uncomment and adjust if you have specific database roles
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO auth_service;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO auth_service;

-- =====================================================
-- MIGRATION COMPLETE
-- =====================================================
-- Authentication infrastructure is now in place.
-- Next steps:
-- 1. Create src/auth/db.py module for database operations
-- 2. Migrate existing YAML users to database
-- 3. Update streamlit_auth.py to use database
-- 4. Implement password reset flow
-- 5. Add OAuth integration
-- 6. Set up cron jobs for:
--    - Cleaning expired sessions (daily)
--    - Cleaning expired reset tokens (daily)
--    - Unlocking expired account lockouts (hourly)
-- =====================================================
