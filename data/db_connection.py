import psycopg2
import psycopg2.pool
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Global variable which will contain pool connections 
# (Pre opened database connections)
_pool = None


def _get_pool():
    """Create connections only if there is none already open
       This will always run on upon the first call
       It reads database information from the .env file to make the connections
    """   
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
    """Used to grab one of the open connections from the pool"""
    try:
        return _get_pool().getconn()
    except Exception as e:
        logger.error("Database connection error: %s", e)
        return None


@contextmanager
def get_db():
    """
    Context manager that opens a connection
    Commits on success, rolls back on exception, returns conn to pool
    """

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
