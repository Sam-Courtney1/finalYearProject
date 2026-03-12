from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

"""
Flask extensions instantiated here to avoid circular imports.
The limiter is initialised with the app in wsgi.py via init_app().

In production, set REDIS_URL (e.g. redis://your-redis-host:6379) so that
rate limits persist across app restarts and work correctly behind a
load balancer with multiple instances. Falls back to in-memory storage
for local development.
"""

_storage_uri = os.getenv("REDIS_URL", "memory://")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=_storage_uri
)
