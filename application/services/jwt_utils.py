import jwt
import os
from datetime import datetime, timedelta

# Uses the same encryption key as the rest of the app to sign tokens
JWT_SECRET = os.getenv("APP_ENC_KEY", "test")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


def create_token(user_id, username):
    """Takes a user_id and username, returns a signed JWT token string that expires in 24 hours"""
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.utcnow()
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
