from data.db_connection import get_db
import os
import logging

logger = logging.getLogger(__name__)

# Tracks email notifications sent to users about data breaches.

def _row_to_dict(cur, row):
    """Convert a single database row to a dict using cursor column names. Dictionaries are easier to work with then tuples"""
    columns = [desc[0] for desc in cur.description]
    return dict(zip(columns, row))


def _rows_to_dicts(cur, rows):
    """Convert database rows to a list of dicts using cursor column names. Dictionaries are easier to work with then tuples"""
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in rows]


def insert_breach_notification(breach_id, user_id, email_address):
    """Insert a pending notification record. Returns notification_id or None. This is before any email is sent"""
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                INSERT INTO breach_notifications
                    (breach_id, user_id, email_address, status)
                VALUES (%s, %s, %s, 'pending')
                RETURNING notification_id;
            """, (breach_id, user_id, email_address))
            return cur.fetchone()[0]
    except Exception as e:
        logger.error("Error inserting breach notification: %s", e)
        return None


def update_notification_status(notification_id, status, error_message=None):
    """Update notification status after send attempt. Sets sent_at on success."""
    try:
        with get_db() as (conn, cur):
            if status == 'sent':
                cur.execute("""
                    UPDATE breach_notifications
                    SET status = %s, sent_at = NOW(), error_message = NULL
                    WHERE notification_id = %s;
                """, (status, notification_id))
            else:
                cur.execute("""
                    UPDATE breach_notifications
                    SET status = %s, error_message = %s
                    WHERE notification_id = %s;
                """, (status, error_message, notification_id))
            return True
    except Exception as e:
        logger.error("Error updating notification %s: %s", notification_id, e)
        return False


def get_notifications_for_breach(breach_id):
    """Returns all notification records for a breach."""
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                SELECT notification_id, breach_id, user_id, email_address,
                       sent_at, status, error_message, created_at
                FROM breach_notifications
                WHERE breach_id = %s
                ORDER BY created_at DESC;
            """, (breach_id,))
            return _rows_to_dicts(cur, cur.fetchall())
    except Exception as e:
        logger.error("Error getting notifications for breach %s: %s", breach_id, e)
        return []


def get_notification_summary(breach_id):
    """Returns notification counts for a breach."""
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status = 'sent') AS sent,
                    COUNT(*) FILTER (WHERE status = 'failed') AS failed,
                    COUNT(*) FILTER (WHERE status = 'pending') AS pending
                FROM breach_notifications
                WHERE breach_id = %s;
            """, (breach_id,))
            row = cur.fetchone()
            return _row_to_dict(cur, row)
    except Exception as e:
        logger.error("Error getting notification summary for breach %s: %s", breach_id, e)
        return {'total': 0, 'sent': 0, 'failed': 0, 'pending': 0}


def get_all_user_emails():
    """
    Returns list of (user_id, email) tuples for all users with an email on file.
    Decrypts email_enc using pgp_sym_decrypt.
    """
    try:
        key = os.getenv("APP_ENC_KEY")
        if not key:
            logger.error("APP_ENC_KEY not set — cannot decrypt emails")
            return []

        with get_db() as (conn, cur):
            cur.execute("""
                SELECT id, pgp_sym_decrypt(email_enc::bytea, %s) AS email
                FROM users
                WHERE email_enc IS NOT NULL;
            """, (key,))
            rows = cur.fetchall()
            return [(row[0], row[1]) for row in rows if row[1]]
    except Exception as e:
        logger.error("Error getting user emails: %s", e)
        return []
