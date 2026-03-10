from data.db_connection import get_db
import logging

logger = logging.getLogger(__name__)

"""
Breach Notification Database Operations
GDPR Articles 33-34

Manages the data_breaches table for tracking security incidents,
their severity, status, and the 72-hour reporting deadline.
"""


def insert_breach(title, description, severity, affected_count, data_types, reported_by):
    """Insert a new data breach record. Returns the breach_id or None on error."""
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                INSERT INTO data_breaches
                    (title, description, severity, affected_users_count,
                     data_types_affected, reported_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING breach_id;
            """, (title, description, severity, affected_count, data_types, reported_by))
            return cur.fetchone()[0]
    except Exception as e:
        logger.error("Error inserting breach: %s", e)
        return None


def get_all_breaches():
    """Returns all breaches ordered by most recent first."""
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                SELECT breach_id, title, description, severity, discovered_at,
                       reported_at, resolved_at, affected_users_count,
                       data_types_affected, remedial_actions, reported_by,
                       status, created_at
                FROM data_breaches
                ORDER BY discovered_at DESC;
            """)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error("Error getting breaches: %s", e)
        return []


def get_breach_by_id(breach_id):
    """Returns a single breach record as a dict, or None."""
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                SELECT breach_id, title, description, severity, discovered_at,
                       reported_at, resolved_at, affected_users_count,
                       data_types_affected, remedial_actions, reported_by,
                       status, created_at
                FROM data_breaches
                WHERE breach_id = %s;
            """, (breach_id,))
            row = cur.fetchone()
            if not row:
                return None
            columns = [desc[0] for desc in cur.description]
            return dict(zip(columns, row))
    except Exception as e:
        logger.error("Error getting breach %s: %s", breach_id, e)
        return None


def update_breach_status(breach_id, status, resolved_at=None, reported_at=None,
                         remedial_actions=None):
    """Update breach status and optional fields. Returns True on success."""
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                UPDATE data_breaches
                SET status = %s,
                    resolved_at = COALESCE(%s, resolved_at),
                    reported_at = COALESCE(%s, reported_at),
                    remedial_actions = COALESCE(%s, remedial_actions)
                WHERE breach_id = %s;
            """, (status, resolved_at, reported_at, remedial_actions, breach_id))
            return True
    except Exception as e:
        logger.error("Error updating breach %s: %s", breach_id, e)
        return False


def get_open_breaches_count():
    """Returns the count of non-resolved breaches."""
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                SELECT COUNT(*) FROM data_breaches
                WHERE status != 'resolved';
            """)
            return cur.fetchone()[0]
    except Exception as e:
        logger.error("Error counting open breaches: %s", e)
        return 0
