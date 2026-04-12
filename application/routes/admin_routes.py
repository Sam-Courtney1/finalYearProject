from flask import Blueprint, render_template, request, session, redirect, url_for, flash, Response, jsonify
from werkzeug.security import check_password_hash
from application.services.decorators import require_audit_access
from application.extensions import limiter
from data.audit_database import (
    get_audit_logs, get_audit_log_count, get_action_summary,
    verify_audit_chain, create_audit_table, find_auditor_by_username
)
from application.services.audit_service import audit_log
from data.retention_database import get_retention_stats, get_inactive_users, get_expired_submissions
from application.services.retention_service import run_retention_cleanup
from data.breach_database import (
    insert_breach, get_all_breaches, get_breach_by_id,
    update_breach_status
)
from application.services.breach_service import check_72h_deadline, get_breach_summary
from application.services.breach_notification_service import notify_all_affected_users
from data.breach_notification_database import get_notifications_for_breach, get_notification_summary
from application.services.dsr_service import get_dsr_dashboard_data
from application.services.compliance_service import get_compliance_overview
import csv
import io
import ipaddress
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse


def _sanitize_csv_value(value):
    """Sanitize a value for CSV export to prevent formula injection.
    Prefixes cells starting with =, +, -, @, \\t, \\r with a single quote."""
    if value is None:
        return ''
    s = str(value)
    if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + s
    return s


"""
Admin Routes Blueprint
Provides audit log dashboard for both clients and external auditors.

Clients see only audit logs related to their own data (filtered by client_id).
External auditors see the full unfiltered audit trail for regulatory compliance.
"""

admin_bp = Blueprint('admin_bp', __name__)


def _require_auditor(message="Only auditors can access this feature."):
    """Return a redirect response if the current user is not an auditor, or None if they are."""
    if 'auditor_id' not in session:
        flash(message, "warning")
        return redirect(url_for('admin_bp.audit_dashboard'))
    return None


def _parse_date_range(date_range_str, default_days=7):
    """Parse a date_range query parameter into a UTC start_date, or None for 'all'."""
    if not date_range_str or date_range_str == 'all':
        return None
    try:
        days = int(date_range_str)
    except (ValueError, TypeError):
        days = default_days
    return datetime.now(timezone.utc) - timedelta(days=days)


@admin_bp.route('/')
@require_audit_access
@audit_log('view', 'audit_logs')
def audit_dashboard():
    """
    Main audit dashboard showing recent logs and statistics.
    Clients see only their own logs (filtered by client_id).
    Auditors see all logs unfiltered.
    """
    # Determine view mode: auditor sees everything, client sees only their data
    is_auditor = 'auditor_id' in session
    filter_client_id = None if is_auditor else session.get('client_id')

    # Get filter parameters
    page = request.args.get('page', 1, type=int)
    per_page = 25
    action_filter = request.args.get('action')
    actor_type_filter = request.args.get('actor_type')
    date_range = request.args.get('date_range', '7')  # days

    start_date = _parse_date_range(date_range, default_days=7)

    # Get logs with pagination (filtered by client_id for clients)
    offset = (page - 1) * per_page
    logs = get_audit_logs(
        limit=per_page,
        offset=offset,
        action=action_filter if action_filter else None,
        actor_type=actor_type_filter if actor_type_filter else None,
        start_date=start_date,
        client_id=filter_client_id
    )

    # Get total count for pagination
    total_count = get_audit_log_count(
        action=action_filter if action_filter else None,
        actor_type=actor_type_filter if actor_type_filter else None,
        start_date=start_date,
        client_id=filter_client_id
    )

    total_pages = (total_count + per_page - 1) // per_page

    # Get action summary for stats
    action_summary = get_action_summary(start_date=start_date, client_id=filter_client_id)

    # Verify chain integrity (always checks full chain)
    chain_valid = verify_audit_chain()

    # Display name depends on who is logged in
    display_name = session.get('auditor_username') if is_auditor else session.get('client_username')

    return render_template(
        'audit_dashboard.html',
        logs=logs,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        action_summary=action_summary,
        chain_valid=chain_valid,
        action_filter=action_filter,
        actor_type_filter=actor_type_filter,
        date_range=date_range,
        client_username=display_name,
        is_auditor=is_auditor
    )


@admin_bp.route('/export')
@require_audit_access
@audit_log('export', 'audit_logs')
def export_audit_logs():
    """
    Export audit logs as CSV file.
    Clients only export their own logs; auditors export all.
    """
    is_auditor = 'auditor_id' in session
    filter_client_id = None if is_auditor else session.get('client_id')

    # Get filter parameters
    action_filter = request.args.get('action')
    actor_type_filter = request.args.get('actor_type')
    date_range = request.args.get('date_range', '30')

    start_date = _parse_date_range(date_range, default_days=30)

    # Get all matching logs (up to 10000), filtered by client_id for clients
    logs = get_audit_logs(
        limit=10000,
        action=action_filter if action_filter else None,
        actor_type=actor_type_filter if actor_type_filter else None,
        start_date=start_date,
        client_id=filter_client_id
    )

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Log ID', 'Timestamp', 'Actor ID', 'Actor Type', 'Action',
        'Target Table', 'Target ID', 'IP Address', 'User Agent', 'Details'
    ])

    # Write data (sanitized to prevent CSV formula injection)
    for log in logs:
        writer.writerow([
            _sanitize_csv_value(log.get('log_id')),
            _sanitize_csv_value(log.get('timestamp')),
            _sanitize_csv_value(log.get('actor_id')),
            _sanitize_csv_value(log.get('actor_type')),
            _sanitize_csv_value(log.get('action')),
            _sanitize_csv_value(log.get('target_table')),
            _sanitize_csv_value(log.get('target_id')),
            _sanitize_csv_value(log.get('ip_address')),
            _sanitize_csv_value(log.get('user_agent')),
            _sanitize_csv_value(log.get('details'))
        ])

    # Create response
    output.seek(0)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=audit_logs_{timestamp}.csv'
        }
    )


@admin_bp.route('/verify-chain')
@require_audit_access
@audit_log('view', 'audit_chain_verification')
def verify_chain():
    """
    Verify the integrity of the audit log hash chain.
    """
    is_valid = verify_audit_chain()

    if is_valid is None:
        flash("Error verifying audit chain. Database connection issue.", "danger")
    elif is_valid:
        flash("Audit log chain integrity verified. No tampering detected.", "success")
    else:
        flash("WARNING: Audit log chain integrity check FAILED. Possible tampering detected!", "danger")

    return redirect(url_for('admin_bp.audit_dashboard'))


@admin_bp.route('/init')
@require_audit_access
def init_audit_table():
    """
    Initialize the audit logs table (first-time setup).
    """
    success = create_audit_table()

    if success:
        flash("Audit table created/verified successfully.", "success")
    else:
        flash("Error creating audit table. Check database connection.", "danger")

    return redirect(url_for('admin_bp.audit_dashboard'))


@admin_bp.route('/auditor-login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def auditor_login():
    """
    Login page for external auditors.
    Auditors have a separate login and see the full unfiltered audit trail.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        auditor = find_auditor_by_username(username)
        if auditor and check_password_hash(auditor[2], password):
            # Clear any stale client session to prevent role bleed
            session.pop('client_id', None)
            session.pop('client_username', None)
            session['auditor_id'] = auditor[0]
            session['auditor_username'] = auditor[1]
            return redirect(url_for('admin_bp.audit_dashboard'))
        else:
            flash("Invalid auditor credentials.", "danger")

    return render_template('auditor_login.html')


@admin_bp.route('/auditor-logout')
def auditor_logout():
    """
    Clear the auditor session and redirect to auditor login.
    """
    session.pop('auditor_id', None)
    session.pop('auditor_username', None)
    return redirect(url_for('admin_bp.auditor_login'))


@admin_bp.route('/geolocate/<ip>')
@require_audit_access
def geolocate_ip(ip):
    """
    Returns geolocation data for a given IP address.
    Uses ip-api.com. Validates IP format and blocks private/loopback
    addresses to prevent SSRF attacks.
    """
    try:
        # Validate IP format and block private/reserved addresses (SSRF protection)
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid IP address format'})

        if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local:
            return jsonify({
                'success': False,
                'message': 'Cannot geolocate private or reserved IP addresses'
            })

        # Construct URL with validated IP, only allow HTTP to ip-api.com (SSRF-safe)
        api_url = f"http://ip-api.com/json/{ip}?fields=status,message,country,city,lat,lon,isp"
        parsed_url = urlparse(api_url)
        if parsed_url.scheme != 'http' or parsed_url.hostname != 'ip-api.com':
            return jsonify({'success': False, 'message': 'Invalid geolocation request'})
        req = urllib.request.Request(api_url, headers={'User-Agent': 'GDPR-Audit-Dashboard'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        if data.get('status') == 'success':
            return jsonify({
                'success': True,
                'ip': ip,
                'city': data.get('city', 'Unknown'),
                'country': data.get('country', 'Unknown'),
                'lat': data.get('lat'),
                'lon': data.get('lon'),
                'isp': data.get('isp', 'Unknown')
            })
        else:
            return jsonify({
                'success': False,
                'message': data.get('message', 'Could not geolocate this IP address')
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Geolocation service unavailable: {str(e)}'
        })


@admin_bp.route('/retention')
@require_audit_access
@audit_log('view', 'retention_dashboard')
def retention_dashboard():
    """
    Data retention dashboard showing inactive users and expired submissions.
    Only accessible to auditors clients should not manage other clients data.
    """
    denied = _require_auditor("Only auditors can access the data retention dashboard.")
    if denied:
        return denied

    days = request.args.get('days', 365, type=int)
    stats = get_retention_stats(days)
    inactive_users = get_inactive_users(days)
    expired_submissions = get_expired_submissions(days)

    return render_template(
        'retention_dashboard.html',
        stats=stats,
        inactive_users=inactive_users,
        expired_submissions=expired_submissions,
        retention_days=days,
        now=datetime.now(timezone.utc),
        client_username=session.get('auditor_username')
    )


@admin_bp.route('/retention/preview', methods=['POST'])
@require_audit_access
@audit_log('view', 'retention_preview')
def retention_preview():
    """Preview what data would be deleted by a retention cleanup (dry run)."""
    denied = _require_auditor("Only auditors can run retention cleanup.")
    if denied:
        return denied

    days = request.form.get('days', 365, type=int)
    days = max(1, min(days, 3650))  # Clamp to valid range
    result = run_retention_cleanup(days=days, dry_run=True)

    flash(f"Preview: {result['inactive_users_count']} inactive users and "
          f"{result['expired_submissions_count']} expired submissions would be affected.", "info")
    return redirect(url_for('admin_bp.retention_dashboard', days=days))


@admin_bp.route('/retention/cleanup', methods=['POST'])
@require_audit_access
@audit_log('delete', 'retention_cleanup')
def retention_cleanup():
    """Execute retention cleanup, deletes expired data and logs actions."""
    denied = _require_auditor("Only auditors can run retention cleanup.")
    if denied:
        return denied

    days = request.form.get('days', 365, type=int)
    days = max(1, min(days, 3650))  # Clamp to valid range
    result = run_retention_cleanup(days=days, dry_run=False)

    flash(f"Retention cleanup complete: {result['deleted_submissions']} submissions deleted, "
          f"{result['anonymised_users']} inactive user accounts cleaned up.", "success")
    return redirect(url_for('admin_bp.retention_dashboard', days=days))


@admin_bp.route('/breaches')
@require_audit_access
@audit_log('view', 'data_breaches')
def breach_dashboard():
    """
    Breach notification dashboard listing all recorded data breaches.
    Shows 72 hour reporting deadline countdown.
    """
    denied = _require_auditor("Only auditors can access the breach register.")
    if denied:
        return denied

    breaches = get_all_breaches()
    summary = get_breach_summary()

    # Add deadline info to each breach
    for breach in breaches:
        breach['hours_remaining'] = check_72h_deadline(breach)

    return render_template(
        'breach_dashboard.html',
        breaches=breaches,
        summary=summary,
        client_username=session.get('auditor_username')
    )


@admin_bp.route('/breaches', methods=['POST'])
@require_audit_access
@audit_log('create', 'data_breaches')
def create_breach():
    """Log a new data breach incident."""
    denied = _require_auditor("Only auditors can log breaches.")
    if denied:
        return denied

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    severity = request.form.get('severity', 'medium')
    affected_count = request.form.get('affected_users_count', 0, type=int)
    data_types = request.form.get('data_types_affected', '').strip()

    if not title:
        flash("Breach title is required.", "danger")
        return redirect(url_for('admin_bp.breach_dashboard'))

    breach_id = insert_breach(
        title=title,
        description=description,
        severity=severity,
        affected_count=affected_count,
        data_types=data_types,
        reported_by=session.get('auditor_id')
    )

    if breach_id:
        flash(f"Breach #{breach_id} logged successfully. 72 hour reporting deadline is now active.", "success")
    else:
        flash("Error logging breach. Please try again.", "danger")

    return redirect(url_for('admin_bp.breach_dashboard'))


@admin_bp.route('/breaches/<int:breach_id>')
@require_audit_access
@audit_log('view', 'data_breaches')
def breach_detail(breach_id):
    """View detailed information about a specific breach."""
    denied = _require_auditor("Only auditors can view breach details.")
    if denied:
        return denied

    breach = get_breach_by_id(breach_id)
    if not breach:
        flash("Breach not found.", "danger")
        return redirect(url_for('admin_bp.breach_dashboard'))

    breach['hours_remaining'] = check_72h_deadline(breach)

    # Get notification data for this breach
    notifications = get_notifications_for_breach(breach_id)
    notif_summary = get_notification_summary(breach_id)

    return render_template(
        'breach_detail.html',
        breach=breach,
        notifications=notifications,
        notif_summary=notif_summary,
        client_username=session.get('auditor_username')
    )


@admin_bp.route('/breaches/<int:breach_id>/notify', methods=['POST'])
@require_audit_access
@audit_log('create', 'breach_notifications')
def notify_breach_users(breach_id):
    """Send breach notification emails to all affected users."""
    denied = _require_auditor("Only auditors can send breach notifications.")
    if denied:
        return denied

    result = notify_all_affected_users(breach_id)

    if result['total'] == 0:
        flash("No users with email addresses found to notify.", "info")
    else:
        flash(f"Breach notification sent: {result['sent']} delivered, "
              f"{result['failed']} failed out of {result['total']} users.", "success")

    return redirect(url_for('admin_bp.breach_detail', breach_id=breach_id))


@admin_bp.route('/breaches/<int:breach_id>/update', methods=['POST'])
@require_audit_access
@audit_log('update', 'data_breaches')
def update_breach(breach_id):
    """Update the status and remedial actions of a breach."""
    denied = _require_auditor("Only auditors can update breaches.")
    if denied:
        return denied

    status = request.form.get('status', '')
    remedial_actions = request.form.get('remedial_actions', '').strip()

    reported_at = None
    resolved_at = None
    if status == 'reported':
        reported_at = datetime.now(timezone.utc)
    elif status == 'resolved':
        resolved_at = datetime.now(timezone.utc)

    success = update_breach_status(
        breach_id=breach_id,
        status=status,
        resolved_at=resolved_at,
        reported_at=reported_at,
        remedial_actions=remedial_actions
    )

    if success:
        flash(f"Breach #{breach_id} updated to '{status}'.", "success")
    else:
        flash("Error updating breach.", "danger")

    return redirect(url_for('admin_bp.breach_detail', breach_id=breach_id))


@admin_bp.route('/dsr')
@require_audit_access
@audit_log('view', 'data_subject_requests')
def dsr_dashboard():
    """
    DSR dashboard showing all data subject requests with 30 day deadlines.
    Only accessible to auditors.
    """
    denied = _require_auditor("Only auditors can access the DSR dashboard.")
    if denied:
        return denied

    status_filter = request.args.get('status')
    data = get_dsr_dashboard_data(status_filter=status_filter if status_filter else None)

    return render_template(
        'dsr_dashboard.html',
        dsrs=data['dsrs'],
        summary=data['summary'],
        status_filter=status_filter,
        client_username=session.get('auditor_username')
    )


@admin_bp.route('/compliance')
@require_audit_access
@audit_log('view', 'compliance_dashboard')
def compliance_dashboard():
    """
    Overall GDPR compliance dashboard aggregating breach, DSR,
    retention, and backup status into a single overview.
    """
    denied = _require_auditor("Only auditors can access the compliance dashboard.")
    if denied:
        return denied

    overview = get_compliance_overview()

    return render_template(
        'compliance_dashboard.html',
        overview=overview,
        client_username=session.get('auditor_username')
    )
