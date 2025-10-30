"""Email verification flow implementation.

Provides secure email verification functionality for new user registrations.
"""

import secrets
from datetime import UTC, datetime, timedelta

import structlog

from src.auth.db import get_user_by_id
from src.auth.hash_password import hash_password, verify_password
from src.clients.database import get_supabase_client
from src.config import get_settings

logger = structlog.get_logger(__name__)


async def create_verification_token(
    user_id: str, expires_in_hours: int = 24, created_ip: str | None = None
) -> str:
    """Create email verification token for user.

    Args:
        user_id: User ID
        expires_in_hours: Token expiration time (default 24 hours)
        created_ip: IP address of request

    Returns:
        Verification token (to be sent in email)

    Raises:
        Exception: If token creation fails
    """
    client = get_supabase_client()

    # Generate secure random token
    token = secrets.token_urlsafe(32)  # 256-bit token
    token_hash = hash_password(token)  # Hash for storage

    # Calculate expiration
    expires_at = (datetime.now(UTC) + timedelta(hours=expires_in_hours)).isoformat()

    # Store token
    token_data = {
        "user_id": user_id,
        "token": token,
        "token_hash": token_hash,
        "expires_at": expires_at,
        "created_ip": created_ip,
    }

    response = client.table("auth_email_verification_tokens").insert(token_data).execute()

    if not response.data:
        raise Exception("Failed to create verification token")

    logger.info(
        "Email verification token created", user_id=user_id, expires_in_hours=expires_in_hours
    )
    return token


async def verify_verification_token(token: str) -> dict | None:
    """Verify email verification token.

    Args:
        token: Verification token from URL

    Returns:
        Token record if valid and not expired, None otherwise
    """
    client = get_supabase_client()

    try:
        # Get all unused, non-expired tokens
        response = (
            client.table("auth_email_verification_tokens")
            .select("*")
            .is_("verified_at", "null")
            .gt("expires_at", datetime.now(UTC).isoformat())
            .execute()
        )

        if not response.data:
            logger.warning("No valid verification tokens found")
            return None

        # Check each token's hash
        for token_record in response.data:
            if verify_password(token, token_record["token_hash"]):
                logger.info("Verification token validated", token_id=token_record["id"])
                return token_record

        logger.warning("Token verification failed - no matching hash")
        return None

    except Exception as e:
        logger.error("Token verification failed", error=str(e))
        return None


async def use_verification_token(token: str, verified_ip: str | None = None) -> bool:
    """Mark verification token as used and verify user's email.

    Args:
        token: Verification token
        verified_ip: IP address of verification request

    Returns:
        True if successful

    Raises:
        Exception: If token is invalid or email verification fails
    """
    # Verify token
    token_record = await verify_verification_token(token)

    if not token_record:
        raise Exception("Invalid or expired verification token")

    client = get_supabase_client()

    try:
        # Mark token as used
        verified_at = datetime.now(UTC).isoformat()
        client.table("auth_email_verification_tokens").update(
            {"verified_at": verified_at, "verified_ip": verified_ip}
        ).eq("id", token_record["id"]).execute()

        # Update user's email verification status
        user_update = {
            "is_email_verified": True,
            "email_verified_at": verified_at,
        }

        response = (
            client.table("auth_users")
            .update(user_update)
            .eq("id", token_record["user_id"])
            .execute()
        )

        if not response.data:
            raise Exception("Failed to update user verification status")

        logger.info("Email verified successfully", user_id=token_record["user_id"])
        return True

    except Exception as e:
        logger.error("Failed to use verification token", error=str(e))
        raise


async def send_verification_email_smtp(
    email: str, verification_token: str, verification_url: str, user_name: str
) -> bool:
    """Send email verification email via SMTP.

    Args:
        email: Recipient email address
        verification_token: Email verification token
        verification_url: Base URL for verification (e.g., https://app.example.com/verify-email)
        user_name: User's name for personalization

    Returns:
        True if email sent successfully
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    settings = get_settings()

    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Verify Your Email - Luminari Agent"
        msg["From"] = settings.smtp_from_email
        msg["To"] = email

        # Create verification link with action parameter to distinguish from password reset
        verification_link = f"{verification_url}?token={verification_token}&action=verify"

        # Email body (HTML)
        html = f"""
        <html>
          <head></head>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px;">
              <h1 style="color: white; text-align: center;">🤖 Luminari Agent</h1>
              <div style="background: white; padding: 30px; border-radius: 10px; margin-top: 20px;">
                <h2 style="color: #333;">Welcome, {user_name}!</h2>
                <p>Thank you for registering with Luminari Agent. To complete your registration and activate your account, please verify your email address.</p>

                <div style="text-align: center; margin: 30px 0;">
                  <a href="{verification_link}" style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Verify Email Address</a>
                </div>

                <p style="color: #666; font-size: 14px;">Or copy and paste this link into your browser:</p>
                <p style="background: #f5f5f5; padding: 10px; border-radius: 5px; word-break: break-all; font-size: 12px; color: #666;">{verification_link}</p>

                <p style="color: #666; font-size: 14px; margin-top: 30px;">
                  <strong>This link will expire in 24 hours.</strong>
                </p>

                <div style="margin-top: 30px; padding: 15px; background: #e8f4f8; border-radius: 6px; border-left: 4px solid #667eea;">
                  <p style="margin: 0; font-size: 14px; color: #333;">
                    <strong>Why verify your email?</strong><br>
                    Email verification helps us ensure the security of your account and enables important features like password reset.
                  </p>
                </div>

                <p style="color: #999; font-size: 12px; margin-top: 20px; border-top: 1px solid #eee; padding-top: 20px;">
                  If you didn't create this account, you can safely ignore this email. Your email address will not be used.
                </p>
              </div>
            </div>
          </body>
        </html>
        """

        # Attach HTML
        msg.attach(MIMEText(html, "html"))

        # Send email
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

        logger.info("Email verification email sent", email=email)
        return True

    except Exception as e:
        logger.error("Failed to send verification email", email=email, error=str(e))
        return False


async def send_verification_email(
    email: str, verification_token: str, verification_url: str, user_name: str = "User"
) -> bool:
    """Send email verification email (provider-agnostic).

    Args:
        email: Recipient email address
        verification_token: Email verification token
        verification_url: Base URL for verification
        user_name: User's name for personalization

    Returns:
        True if email sent successfully
    """
    settings = get_settings()

    if not settings.email_enabled:
        logger.warning(
            "Email disabled, verification token generated but not sent",
            email=email,
            token_preview=verification_token[:8] + "...",
        )
        # In development, log the token for testing
        logger.debug(
            "Verification token (dev only)", token=verification_token, url=verification_url
        )
        return False

    if settings.email_provider == "smtp":
        return await send_verification_email_smtp(
            email, verification_token, verification_url, user_name
        )

    logger.error("Unsupported email provider", provider=settings.email_provider)
    return False


async def request_email_verification(user_id: str, verification_url: str) -> tuple[bool, str]:
    """Request email verification for a user.

    Args:
        user_id: User ID
        verification_url: Base URL for verification page

    Returns:
        Tuple of (success, message)
    """
    try:
        # Get user info
        user = get_user_by_id(user_id)

        if not user:
            logger.error("User not found for verification", user_id=user_id)
            return (False, "User not found.")

        # Check if already verified
        if user.get("is_email_verified"):
            logger.info("User email already verified", user_id=user_id)
            return (True, "Email is already verified.")

        # Generate verification token
        verification_token = await create_verification_token(user_id=user_id, expires_in_hours=24)

        # Send verification email
        email = user.get("email")
        user_name = user.get("full_name", "User")
        email_sent = await send_verification_email(
            email, verification_token, verification_url, user_name
        )

        if email_sent:
            logger.info("Verification email sent", user_id=user_id, email=email)
            return (True, "Verification email sent! Please check your inbox.")

        logger.warning("Verification token created but email not sent", user_id=user_id)
        return (
            True,
            "Verification email could not be sent. Please contact support.",
        )

    except Exception as e:
        logger.error("Email verification request failed", error=str(e))
        return (False, "An error occurred. Please try again later.")


async def check_user_email_verified(user_id: str) -> bool:
    """Check if user's email is verified.

    Args:
        user_id: User ID

    Returns:
        True if email is verified
    """
    try:
        user = get_user_by_id(user_id)
        return user.get("is_email_verified", False) if user else False
    except Exception:
        return False
