from data.db_connection import get_db
import logging

logger = logging.getLogger(__name__)

"""
Data Subject Request (DSR) Database Operations

Tracks formal data subject requests (access, erasure, portability, rectification).
"""


def _row_to_dict(cur, row):
    """Convert a database row to a dict using cursor column names."""
    columns = [desc[0] for desc in cur.description]
    return dict(zip(columns, row))


def _rows_to_dicts(cur, rows):
    """Convert database rows to a list of dicts using cursor column names."""
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in rows]


def insert_dsr(user_id, username, request_type, source='web'):
    """
    Insert a new DSR record with a 30-day deadline. Returns dsr_id or None.
    Completed time is set to now as in the UI, the operation occurs instantly.
    """
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                INSERT INTO data_subject_requests
                    (user_id, username, request_type, status, deadline, source)
                VALUES (%s, %s, %s, 'completed', NOW() + INTERVAL '30 days', %s)
                RETURNING dsr_id;
            """, (user_id, username, request_type, source))
            return cur.fetchone()[0]
    except Exception as e:
        logger.error("Error inserting DSR: %s", e)
        return None


def get_all_dsrs(status=None, limit=100, offset=0):
    """Returns all DSRs, optionally filtered by status."""
    try:
        with get_db() as (conn, cur):
            if status:
                cur.execute("""
                    SELECT dsr_id, user_id, username, request_type, status,
                           created_at, completed_at, deadline, notes, source
                    FROM data_subject_requests
                    WHERE status = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s;
                """, (status, limit, offset))
            else:
                cur.execute("""
                    SELECT dsr_id, user_id, username, request_type, status,
                           created_at, completed_at, deadline, notes, source
                    FROM data_subject_requests
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s;
                """, (limit, offset))
            return _rows_to_dicts(cur, cur.fetchall())
    except Exception as e:
        logger.error("Error getting DSRs: %s", e)
        return []


def get_dsr_summary():
    """Returns summary counts for the compliance dashboard."""
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'pending') AS pending_count,
                    COUNT(*) FILTER (WHERE status = 'in_progress') AS in_progress_count,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed_count,
                    COUNT(*) FILTER (WHERE status IN ('pending', 'in_progress')
                                     AND deadline < NOW()) AS overdue_count
                FROM data_subject_requests;
            """)
            row = cur.fetchone()
            return _row_to_dict(cur, row)
    except Exception as e:
        logger.error("Error getting DSR summary: %s", e)
        return {
            'pending_count': 0,
            'in_progress_count': 0,
            'completed_count': 0,
            'overdue_count': 0
        }


def get_dsrs_for_user(user_id):
    """Returns all DSRs for a specific user, for user dashboard."""
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                SELECT dsr_id, request_type, status, created_at, completed_at, deadline
                FROM data_subject_requests
                WHERE user_id = %s
                ORDER BY created_at DESC;
            """, (user_id,))
            return _rows_to_dicts(cur, cur.fetchall())
    except Exception as e:
        logger.error("Error getting DSRs for user %s: %s", user_id, e)
        return []
