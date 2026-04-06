import secrets
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from data.db_connection import get_db

logger = logging.getLogger(__name__)


MAX_OTP_ATTEMPTS = 3


def generate_otp() -> str:
    """Generate a cryptographically random 6 digit OTP code."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_token(token: str) -> str:
    """Return the SHA 256 hex digest of a token string."""
    return hashlib.sha256(token.encode()).hexdigest()


def store_otp(user_id: int, otp_code: str) -> bool:
    """
    Invalidate any existing OTP for this user and store a new one.
    Expiry is 10 minutes from now.
    Returns True on success.
    """
    try:
        with get_db() as (conn, cur):
            # Lock existing unused tokens to prevent race conditions, then invalidate
            cur.execute("""
                SELECT 1 FROM otp_tokens
                WHERE user_id = %s AND used = FALSE
                FOR UPDATE;
            """, (user_id,))
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

            token_id, stored_hash, expires_at, _used, attempts = row
            mark_used = False

            # Already exhausted all attempts — block immediately
            if attempts >= MAX_OTP_ATTEMPTS:
                mark_used = True
                result = (False, 'max_attempts')
            else:
                # Increment attempt counter
                cur.execute("""
                    UPDATE otp_tokens SET attempts = attempts + 1 WHERE id = %s;
                """, (token_id,))

                now = datetime.now(timezone.utc)
                if now > expires_at:
                    mark_used = True
                    result = (False, 'expired')
                elif hash_token(entered_code) != stored_hash:
                    if attempts + 1 >= MAX_OTP_ATTEMPTS:
                        mark_used = True
                    result = (False, 'max_attempts' if mark_used else 'invalid')
                else:
                    mark_used = True
                    result = (True, 'ok')

            if mark_used:
                cur.execute("UPDATE otp_tokens SET used = TRUE WHERE id = %s;", (token_id,))

            return result

    except Exception as e:
        logger.error("Error verifying OTP: %s", e)
        return False, 'not_found'


def generate_reset_token() -> str:
    """Generate a cryptographically random URL safe token for password reset."""
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
    except Exception:
        logger.error("Failed to store password reset request for user_id=%s", user_id)
        return False


def verify_reset_token(token: str) -> int | None:
    """
    Verify a password reset token.
    Returns the user_id if valid and not expired, otherwise None.
    Does NOT mark the token as used, call invalidate_reset_token() after password change.
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

            _token_id, user_id, expires_at = row
            if datetime.now(timezone.utc) > expires_at:
                return None

            return user_id
    except Exception:
        logger.error("Failed to verify password reset request")
        return None


def invalidate_reset_token(token: str) -> None:
    """Mark a password reset token as used after a successful password change."""
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                UPDATE password_reset_tokens SET used = TRUE
                WHERE token_hash = %s;
            """, (hash_token(token),))
    except Exception:
        logger.error("Failed to invalidate password reset request")
