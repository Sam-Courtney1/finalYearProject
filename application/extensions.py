from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

"""
Flask extensions instantiated here to avoid circular imports.
The limiter is initialised with the app in wsgi.py via init_app().
"""

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)
