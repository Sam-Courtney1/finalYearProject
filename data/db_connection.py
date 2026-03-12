import psycopg2
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# This file connects to the database using pyscog2
# The variables are stored in a .env file rather then being hardcoded
# This ensures they are not pushed to GitHub and leaked
# They are also stored in AWS under secrets manager
# In this configuration the database can be connected to securly
# without leaking any sensitive information


def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        return conn
    except Exception as e:
        logger.error("Database connection error: %s", e)
        return None


@contextmanager
def get_db():
    """Context manager that yields (conn, cur).
    Commits on success, rolls back on exception, always closes."""
    conn = get_db_connection()
    if conn is None:
        raise ConnectionError("Could not connect to the database")
    cur = conn.cursor()
    try:
        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
