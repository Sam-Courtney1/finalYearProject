from datetime import datetime, timezone
from data.breach_database import get_all_breaches, get_open_breaches_count
import logging

logger = logging.getLogger(__name__)


def check_72h_deadline(breach):
    """
    Returns hours remaining until the 72 hour GDPR reporting deadline.
    Negative value means the deadline has passed.
    Returns None if breach has already been reported or resolved.
    """
    if breach.get('reported_at') or breach.get('status') == 'resolved':
        return None

    discovered_at = breach.get('discovered_at')
    if not discovered_at:
        return None

    # Ensure timezone-aware comparison
    now = datetime.now(timezone.utc)
    if discovered_at.tzinfo is None:
        discovered_at = discovered_at.replace(tzinfo=timezone.utc)

    elapsed = now - discovered_at
    remaining_hours = 72 - (elapsed.total_seconds() / 3600)
    return round(remaining_hours, 1)


def get_breach_summary():
    """
    Returns summary statistics for the breach dashboard.
    """
    breaches = get_all_breaches()
    open_count = get_open_breaches_count()
    total_count = len(breaches)
    resolved_count = sum(1 for b in breaches if b.get('status') == 'resolved')

    # Count overdue breaches (past 72h, not yet reported)
    overdue_count = 0
    for b in breaches:
        if b.get('status') not in ('reported', 'resolved'):
            hours = check_72h_deadline(b)
            if hours is not None and hours < 0:
                overdue_count += 1

    return {
        'open_count': open_count,
        'total_count': total_count,
        'resolved_count': resolved_count,
        'overdue_count': overdue_count
    }
