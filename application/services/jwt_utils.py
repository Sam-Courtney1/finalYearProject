import jwt
import os
import warnings
from datetime import datetime, timedelta, timezone

# Uses the same encryption key as the rest of the app to sign tokens
# Guarded the same way as wsgi.py — refuses to start in production without it
JWT_SECRET = os.getenv("APP_ENC_KEY")
if not JWT_SECRET or JWT_SECRET == "test":
    if os.getenv("AWS_EXECUTION_ENV"):
        raise RuntimeError("APP_ENC_KEY must be set in production for JWT signing.")
    warnings.warn("JWT_SECRET not set — using insecure default. Set APP_ENC_KEY in .env.")
    JWT_SECRET = "insecure-dev-jwt-do-not-use-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


def create_token(user_id, username):
    """Takes a user_id and username, returns a signed JWT token string that expires in 24 hours"""
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token):
    """Takes a token string and returns the payload (user_id, username) if valid, or None if expired or invalid"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
