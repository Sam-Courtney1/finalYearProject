import secrets
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from data.db_connection import get_db

logger = logging.getLogger(__name__)

"""
OTP Service - One-Time Password generation and verification.
Used for both:
  - Email 2FA codes (6-digit, 10-minute expiry, max 3 attempts)
  - Password reset tokens (URL-safe random string, 1-hour expiry)

Tokens are never stored in plain text — only their SHA-256 hash is kept.
"""

MAX_OTP_ATTEMPTS = 3


def generate_otp() -> str:
    """Generate a cryptographically-random 6-digit OTP code."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a token string."""
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# 2FA OTP functions
# ---------------------------------------------------------------------------

def store_otp(user_id: int, otp_code: str) -> bool:
    """
    Invalidate any existing OTP for this user and store a new one.
    Expiry is 10 minutes from now.
    Returns True on success.
    """
    try:
        with get_db() as (conn, cur):
            # Invalidate previous tokens for this user
            cur.execute("""
                UPDATE otp_tokens SET used = TRUE
                WHERE user_id = %s AND used = FALSE;
            """, (user_id,))

            expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
            cur.execute("""
                INSERT INTO otp_tokens (user_id, token_hash, expires_at)
                VALUES (%s, %s, %s);
            """, (user_id, hash_token(otp_code), expires_at))
        return True
    except Exception as e:
        logger.error("Error storing OTP: %s", e)
        return False


def verify_otp(user_id: int, entered_code: str) -> tuple[bool, str]:
    """
    Verify the OTP entered by a user.
    Returns (success: bool, reason: str).
    Reasons: 'ok', 'invalid', 'expired', 'max_attempts', 'not_found'
    """
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                SELECT id, token_hash, expires_at, used, attempts
                FROM otp_tokens
                WHERE user_id = %s AND used = FALSE
                ORDER BY created_at DESC
                LIMIT 1;
            """, (user_id,))
            row = cur.fetchone()

            if not row:
                return False, 'not_found'

            token_id, stored_hash, expires_at, used, attempts = row

            # Check attempt count first
            if attempts >= MAX_OTP_ATTEMPTS:
                return False, 'max_attempts'

            # Increment attempt counter
            cur.execute("""
                UPDATE otp_tokens SET attempts = attempts + 1 WHERE id = %s;
            """, (token_id,))

            # Check expiry
            now = datetime.now(timezone.utc)
            if now > expires_at:
                cur.execute("UPDATE otp_tokens SET used = TRUE WHERE id = %s;", (token_id,))
                return False, 'expired'

            # Verify hash
            if hash_token(entered_code) != stored_hash:
                # If this was the last allowed attempt, mark as used
                if attempts + 1 >= MAX_OTP_ATTEMPTS:
                    cur.execute("UPDATE otp_tokens SET used = TRUE WHERE id = %s;", (token_id,))
                return False, 'invalid'

            # Success — mark token as used
            cur.execute("UPDATE otp_tokens SET used = TRUE WHERE id = %s;", (token_id,))
            return True, 'ok'

    except Exception as e:
        logger.error("Error verifying OTP: %s", e)
        return False, 'not_found'


# ---------------------------------------------------------------------------
# Password reset token functions
# ---------------------------------------------------------------------------

def generate_reset_token() -> str:
    """Generate a cryptographically-random URL-safe token for password reset."""
    return secrets.token_urlsafe(32)


def store_reset_token(user_id: int, token: str) -> bool:
    """
    Invalidate any existing reset token for this user and store a new one.
    Expiry is 1 hour from now.
    Returns True on success.
    """
    try:
        with get_db() as (conn, cur):
            # Invalidate previous reset tokens for this user
            cur.execute("""
                UPDATE password_reset_tokens SET used = TRUE
                WHERE user_id = %s AND used = FALSE;
            """, (user_id,))

            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            cur.execute("""
                INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
                VALUES (%s, %s, %s);
            """, (user_id, hash_token(token), expires_at))
        return True
    except Exception as e:
        logger.error("Error storing reset token: %s", e)
        return False


def verify_reset_token(token: str) -> int | None:
    """
    Verify a password reset token.
    Returns the user_id if valid and not expired, otherwise None.
    Does NOT mark the token as used — call invalidate_reset_token() after password change.
    """
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                SELECT id, user_id, expires_at
                FROM password_reset_tokens
                WHERE token_hash = %s AND used = FALSE
                ORDER BY created_at DESC
                LIMIT 1;
            """, (hash_token(token),))
            row = cur.fetchone()

            if not row:
                return None

            token_id, user_id, expires_at = row
            if datetime.now(timezone.utc) > expires_at:
                return None

            return user_id
    except Exception as e:
        logger.error("Error verifying reset token: %s", e)
        return None


def invalidate_reset_token(token: str) -> None:
    """Mark a password reset token as used after a successful password change."""
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                UPDATE password_reset_tokens SET used = TRUE
                WHERE token_hash = %s;
            """, (hash_token(token),))
    except Exception as e:
        logger.error("Error invalidating reset token: %s", e)
