from application.services.breach_service import get_breach_summary
from data.dsr_database import get_dsr_summary
from data.retention_database import get_retention_stats
import logging

logger = logging.getLogger(__name__)

"""
Aggregates metrics from breach, DSR, and retention modules
to provide a single compliance overview for the dashboard
"""


def get_compliance_overview(retention_days=365):
    """
    Returns a dict with compliance status across all GDPR areas.
    Overall status: compliant (green), attentio' (amber), or non_compliant (red).
    """
    breach = get_breach_summary()
    dsr = get_dsr_summary()
    retention = get_retention_stats(retention_days)

    # Calculate overall status
    overall_status = 'compliant'

    # Red: any overdue breaches or overdue DSRs
    if breach.get('overdue_count', 0) > 0 or dsr.get('overdue_count', 0) > 0:
        overall_status = 'non_compliant'
    # Amber: open breaches, pending DSRs older than threshold, or high inactive users
    elif breach.get('open_count', 0) > 0 or dsr.get('pending_count', 0) > 0:
        overall_status = 'attention'
    elif retention.get('inactive_users', 0) > 0 or retention.get('expired_submissions', 0) > 0:
        overall_status = 'attention'

    backup = {
        'enabled': True,
        'retention_days': 7,
        'window': '04:00-04:30 UTC',
        'provider': 'AWS RDS Automated Snapshots'
    }

    return {
        'breach': breach,
        'dsr': dsr,
        'retention': retention,
        'backup': backup,
        'overall_status': overall_status
    }
