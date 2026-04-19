import jwt
import os
import uuid
import warnings
from datetime import datetime, timedelta, timezone

# Separate JWT signing key, distinct from the database encryption key 
# and the Flask session key so a compromise of one does not affect the others.
JWT_SECRET = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET:
    if os.getenv("AWS_EXECUTION_ENV") or os.getenv("FLASK_ENV") == "production" or os.getenv("PRODUCTION"):
        raise RuntimeError("JWT_SECRET_KEY must be set in production for JWT signing.")
    warnings.warn("JWT_SECRET_KEY not set, using insecure default. Set it in .env.")
    JWT_SECRET = "insecure-dev-jwt-do-not-use-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 2

# In memory revocation list, tokens added here are rejected by decode_token.
# Entries auto expire when the JWT itself expires, so the set stays bounded.
_revoked_jtis = set()


def create_token(user_id, username):
    """Takes a user_id and username, returns a signed JWT token string that expires in 2 hours"""
    payload = {
        "user_id": user_id,
        "username": username,
        "jti": uuid.uuid4().hex,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token):
    """Takes a token string and returns the payload (user_id, username) if valid, or None if expired/invalid/revoked"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("jti") in _revoked_jtis:
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def revoke_token(token):
    """Add a tokens JTI to the revocation list so it is rejected on future requests."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
                             options={"verify_exp": False})
        jti = payload.get("jti")
        if jti:
            _revoked_jtis.add(jti)
    except jwt.InvalidTokenError:
        pass
