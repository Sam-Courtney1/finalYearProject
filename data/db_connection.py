import psycopg2
import psycopg2.pool
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# This file connects to the database using psycopg2
# The variables are stored in a .env file rather then being hardcoded
# This ensures they are not pushed to GitHub and leaked
# They are also stored in AWS under secrets manager
# In this configuration the database can be connected to securly
# without leaking any sensitive information

_pool = None


def _get_pool():
    """Lazily initialise a threaded connection pool (1–10 connections)."""
    global _pool
    if _pool is None:
        try:
            _pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=os.getenv("DB_HOST"),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
            )
        except Exception as e:
            logger.error("Database pool creation error: %s", e)
            raise
    return _pool


def get_db_connection():
    try:
        return _get_pool().getconn()
    except Exception as e:
        logger.error("Database connection error: %s", e)
        return None


@contextmanager
def get_db():
    """Context manager that yields (conn, cur).
    Commits on success, rolls back on exception, returns conn to pool."""
    pool = _get_pool()
    conn = pool.getconn()
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
        pool.putconn(conn)
