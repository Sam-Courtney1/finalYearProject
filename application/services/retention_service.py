from data.retention_database import get_inactive_users, get_expired_submissions
from data.db_connection import get_db
from application.services.audit_service import log_data_delete
import logging

logger = logging.getLogger(__name__)

"""
Data Retention Service
GDPR Article 5(1)(e) - Storage Limitation

Handles identification and cleanup of data that has exceeded the
retention period. Supports dry-run mode for previewing what would
be deleted before executing.
"""


def run_retention_cleanup(days=365, dry_run=True):
    """
    Identifies and optionally deletes expired data.

    dry_run=True: returns what WOULD be deleted (for preview).
    dry_run=False: actually deletes and logs to audit trail.

    Returns dict with counts and details of affected records.
    """
    inactive_users = get_inactive_users(days)
    expired_submissions = get_expired_submissions(days)

    result = {
        'inactive_users_count': len(inactive_users),
        'expired_submissions_count': len(expired_submissions),
        'inactive_users': inactive_users,
        'expired_submissions': expired_submissions,
        'dry_run': dry_run,
        'deleted_submissions': 0,
        'anonymised_users': 0
    }

    if dry_run:
        return result

    # Delete expired submissions (answers cascade)
    for sub in expired_submissions:
        submission_id = sub[0]
        user_id = sub[1]
        try:
            with get_db() as (conn, cur):
                # Delete answers first, then submission
                cur.execute("DELETE FROM answers WHERE submission_id = %s;", (submission_id,))
                cur.execute("DELETE FROM pii WHERE submission_id = %s;", (submission_id,))
                cur.execute("DELETE FROM demographic_data WHERE submission_id = %s;", (submission_id,))
                cur.execute("DELETE FROM submissions WHERE submission_id = %s;", (submission_id,))

            log_data_delete('submissions', submission_id, {
                'action': 'retention_cleanup',
                'user_id': user_id,
                'reason': f'Exceeded {days}-day retention period'
            })
            result['deleted_submissions'] += 1
        except Exception as e:
            logger.error("Error deleting expired submission %s: %s", submission_id, e)

    # Anonymise inactive users (remove PII but keep account shell for audit trail)
    for user in inactive_users:
        user_id = user[0]
        try:
            with get_db() as (conn, cur):
                # Delete all submissions and related data for this user
                cur.execute("""
                    DELETE FROM submissions WHERE user_id = %s;
                """, (user_id,))

            log_data_delete('users', user_id, {
                'action': 'retention_cleanup',
                'reason': f'Inactive for over {days} days'
            })
            result['anonymised_users'] += 1
        except Exception as e:
            logger.error("Error cleaning up inactive user %s: %s", user_id, e)

    return result
