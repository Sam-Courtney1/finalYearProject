from datetime import datetime, timezone
from data.dsr_database import insert_dsr, get_all_dsrs, get_dsr_summary
import logging

logger = logging.getLogger(__name__)

"""
Data Subject Request (DSR) Service
GDPR Articles 12-23

Provides helper functions for DSR management including
the 30-day response deadline calculation required by Article 12(3).
"""


def log_dsr(user_id, username, request_type, source='web'):
    """
    Log a DSR when a user exercises a GDPR right.
    Auto-completed since the system fulfils the request immediately.
    Returns the dsr_id or None.
    """
    dsr_id = insert_dsr(user_id, username, request_type, source)
    if dsr_id:
        logger.info("DSR #%s logged: user=%s type=%s source=%s", dsr_id, username, request_type, source)
    return dsr_id


def check_30_day_deadline(dsr):
    """
    Returns days remaining until the 30-day GDPR response deadline.
    Negative value means the deadline has passed.
    Returns None if DSR is already completed.
    """
    if dsr.get('status') == 'completed':
        return None

    deadline = dsr.get('deadline')
    if not deadline:
        return None

    now = datetime.now(timezone.utc)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    remaining = deadline - now
    return remaining.days


def get_dsr_dashboard_data(status_filter=None):
    """
    Returns all DSRs with deadline info for the admin dashboard.
    """
    dsrs = get_all_dsrs(status=status_filter)
    summary = get_dsr_summary()

    for dsr in dsrs:
        dsr['days_remaining'] = check_30_day_deadline(dsr)

    return {
        'dsrs': dsrs,
        'summary': summary
    }
