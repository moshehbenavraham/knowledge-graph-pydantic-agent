"""
Password reset flow implementation.

Provides secure password reset functionality with email-based token verification.
"""

import os

import structlog

from src.auth.db import (
    create_reset_token,
    get_user_by_email,
    get_user_by_username,
    use_reset_token,
    verify_reset_token,
)

logger = structlog.get_logger(__name__)

# Email configuration
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "smtp")  # smtp, sendgrid, mailgun, supabase
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@baseagent.local")


async def send_reset_email_smtp(email: str, reset_token: str, reset_url: str) -> bool:
    """Send password reset email via SMTP.

    Args:
        email: Recipient email address
        reset_token: Password reset token
        reset_url: Base URL for reset (e.g., https://app.example.com/reset-password)

    Returns:
        True if email sent successfully
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Password Reset Request - Base Agent"
        msg["From"] = SMTP_FROM_EMAIL
        msg["To"] = email

        # Create reset link
        reset_link = f"{reset_url}?token={reset_token}"

        # Email body (HTML) - Enhanced professional template
        html = f"""
        <html>
          <head></head>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px;">
              <h1 style="color: white; text-align: center;">🤖 Base Agent</h1>
              <div style="background: white; padding: 30px; border-radius: 10px; margin-top: 20px;">
                <h2 style="color: #333;">Password Reset Request</h2>
                <p>We received a request to reset your password for your Base Agent account. Click the button below to create a new password:</p>

                <div style="text-align: center; margin: 30px 0;">
                  <a href="{reset_link}" style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Reset Password</a>
                </div>

                <p style="color: #666; font-size: 14px;">Or copy and paste this link into your browser:</p>
                <p style="background: #f5f5f5; padding: 10px; border-radius: 5px; word-break: break-all; font-size: 12px; color: #666;">{reset_link}</p>

                <div style="margin-top: 30px; padding: 15px; background: #fff3cd; border-radius: 6px; border-left: 4px solid #ffc107;">
                  <p style="margin: 0; font-size: 14px; color: #856404;">
                    <strong>⏱️ Time Sensitive:</strong> This link will expire in 1 hour for security reasons.
                  </p>
                </div>

                <div style="margin-top: 20px; padding: 15px; background: #e8f4f8; border-radius: 6px; border-left: 4px solid #667eea;">
                  <p style="margin: 0; font-size: 14px; color: #333;">
                    <strong>💡 Password Tips:</strong><br>
                    • Use at least 8 characters<br>
                    • Include uppercase and lowercase letters<br>
                    • Add numbers and special characters<br>
                    • Avoid common words or patterns
                  </p>
                </div>

                <p style="color: #999; font-size: 12px; margin-top: 20px; border-top: 1px solid #eee; padding-top: 20px;">
                  <strong>🔒 Security Notice:</strong> If you didn't request this password reset, please ignore this email. Your password will remain unchanged. For your security, consider changing your password if you believe your account may be compromised.
                </p>

                <p style="color: #999; font-size: 11px; text-align: center; margin-top: 15px;">
                  This is an automated message from Base Agent. Please do not reply to this email.
                </p>
              </div>
            </div>
          </body>
        </html>
        """

        # Attach HTML
        msg.attach(MIMEText(html, "html"))

        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info("Password reset email sent", email=email)
        return True

    except Exception as e:
        logger.error("Failed to send password reset email", email=email, error=str(e))
        return False


async def send_reset_email(email: str, reset_token: str, reset_url: str) -> bool:
    """Send password reset email (provider-agnostic).

    Args:
        email: Recipient email address
        reset_token: Password reset token
        reset_url: Base URL for reset

    Returns:
        True if email sent successfully
    """
    if not EMAIL_ENABLED:
        logger.warning(
            "Email disabled, password reset token generated but not sent",
            email=email,
            token_preview=reset_token[:8] + "...",
        )
        # In development, log the token for testing
        logger.debug("Reset token (dev only)", token=reset_token, reset_url=reset_url)
        return False

    if EMAIL_PROVIDER == "smtp":
        return await send_reset_email_smtp(email, reset_token, reset_url)
    logger.error("Unsupported email provider", provider=EMAIL_PROVIDER)
    return False


async def request_password_reset(
    username_or_email: str, reset_url: str, client_ip: str | None = None
) -> tuple[bool, str]:
    """Request password reset for a user.

    Args:
        username_or_email: Username or email address
        reset_url: Base URL for password reset page
        client_ip: Client IP address (optional)

    Returns:
        Tuple of (success, message)
    """
    try:
        # Find user by username or email
        user = await get_user_by_username(username_or_email)
        if not user:
            user = await get_user_by_email(username_or_email)

        if not user:
            # For security, don't reveal if user exists
            logger.warning(
                "Password reset requested for non-existent user",
                username_or_email=username_or_email,
            )
            return (
                True,
                "If an account exists with that username/email, a password reset link has been sent.",
            )

        # Check if user is active
        if not user.get("is_active"):
            logger.warning(
                "Password reset requested for inactive user", username=user.get("username")
            )
            return (
                True,
                "If an account exists with that username/email, a password reset link has been sent.",
            )

        # Generate reset token
        reset_token = await create_reset_token(
            user_id=user["id"], expires_in_hours=1, created_ip=client_ip
        )

        # Send reset email
        email = user.get("email")
        email_sent = await send_reset_email(email, reset_token, reset_url)

        if email_sent:
            logger.info("Password reset email sent", username=user.get("username"), email=email)
        else:
            logger.warning(
                "Password reset token created but email not sent",
                username=user.get("username"),
                email=email,
            )

        return (
            True,
            "If an account exists with that username/email, a password reset link has been sent.",
        )

    except Exception as e:
        logger.error("Password reset request failed", error=str(e))
        return (False, "An error occurred. Please try again later.")


async def validate_reset_token(token: str) -> tuple[bool, str, dict | None]:
    """Validate a password reset token.

    Args:
        token: Reset token from URL

    Returns:
        Tuple of (is_valid, message, token_record)
    """
    try:
        token_record = await verify_reset_token(token)

        if not token_record:
            logger.warning("Invalid or expired reset token", token_preview=token[:8] + "...")
            return (False, "This password reset link is invalid or has expired.", None)

        return (True, "Token is valid.", token_record)

    except Exception as e:
        logger.error("Token validation failed", error=str(e))
        return (False, "An error occurred. Please try again.", None)


async def reset_password_with_token(
    token: str, new_password: str, client_ip: str | None = None
) -> tuple[bool, str]:
    """Reset password using a valid token.

    Args:
        token: Reset token
        new_password: New password (plain text, will be hashed)
        client_ip: Client IP address (optional)

    Returns:
        Tuple of (success, message)
    """
    try:
        # Use the reset token to change password
        success = await use_reset_token(token, new_password, used_ip=client_ip)

        if success:
            logger.info("Password reset successful via token")
            return (True, "Password reset successful! You can now log in with your new password.")
        logger.warning("Password reset failed with valid token")
        return (False, "Password reset failed. Please try again.")

    except Exception as e:
        logger.error("Password reset failed", error=str(e))

        # Check if it's an invalid token error
        if "Invalid or expired" in str(e):
            return (False, "This password reset link is invalid or has expired.")

        return (False, "An error occurred. Please try again.")


# =====================================================
# Convenience functions for Streamlit integration
# =====================================================


def is_password_strong(password: str) -> tuple[bool, str]:
    """Check if password meets security requirements.

    Args:
        password: Plain text password

    Returns:
        Tuple of (is_strong, message)
    """
    if len(password) < 8:
        return (False, "Password must be at least 8 characters long.")

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    if not (has_upper and has_lower and has_digit):
        return (
            False,
            "Password must contain uppercase, lowercase, and numbers.",
        )

    if not has_special:
        return (
            False,
            "Password should contain at least one special character (!@#$%^&* etc).",
        )

    return (True, "Password is strong.")
