from data.db_connection import get_db
import logging

logger = logging.getLogger(__name__)

"""
Provides queries for identifying inactive users and expired submissions
so that data is not kept longer than necessary.
"""


def get_inactive_users(days=365):
    """
    Returns users who havent logged in for the specified number of days.
    Used by the retention dashboard to identify accounts for cleanup.
    """
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                SELECT id, username, last_login
                FROM users
                WHERE last_login < NOW() - INTERVAL '1 day' * %s
                ORDER BY last_login ASC;
            """, (days,))
            return cur.fetchall()
    except Exception as e:
        logger.error("Error getting inactive users: %s", e)
        return []


def get_expired_submissions(days=365):
    """
    Returns submissions older than the specified number of days
    that have not been deleted and still have active consent.
    """
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                SELECT s.submission_id, s.user_id, u.username, s.created_at,
                       c.username AS client_name
                FROM submissions s
                JOIN users u ON s.user_id = u.id
                LEFT JOIN clients c ON s.client_id = c.client_id
                WHERE s.created_at < NOW() - INTERVAL '1 day' * %s
                  AND (s.deleted = FALSE OR s.deleted IS NULL)
                ORDER BY s.created_at ASC;
            """, (days,))
            return cur.fetchall()
    except Exception as e:
        logger.error("Error getting expired submissions: %s", e)
        return []


def get_retention_stats(days=365):
    """
    Returns retention statistics for the dashboard.
    """
    try:
        with get_db() as (conn, cur):
            cur.execute("SELECT COUNT(*) FROM users;")
            total_users = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*) FROM users
                WHERE last_login < NOW() - INTERVAL '1 day' * %s;
            """, (days,))
            inactive_users = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*) FROM submissions
                WHERE created_at < NOW() - INTERVAL '1 day' * %s
                  AND (deleted = FALSE OR deleted IS NULL);
            """, (days,))
            expired_submissions = cur.fetchone()[0]

            return {
                'total_users': total_users,
                'inactive_users': inactive_users,
                'expired_submissions': expired_submissions,
                'retention_days': days
            }
    except Exception as e:
        logger.error("Error getting retention stats: %s", e)
        return {
            'total_users': 0,
            'inactive_users': 0,
            'expired_submissions': 0,
            'retention_days': days
        }
