from flask import Blueprint, render_template, request, session, redirect, url_for, flash, Response, jsonify
from data.audit_database import (
    get_audit_logs, get_audit_log_count, get_action_summary,
    verify_audit_chain, create_audit_table
)
from application.services.audit_service import audit_log
import csv
import io
import json
import urllib.request
from datetime import datetime, timedelta

"""
Admin Routes Blueprint
Provides audit log dashboard and management for data controllers 
(clients for now but later will be changed to external users / auditors).

Access is restricted to logged in clients who need
to review data access patterns for GDPR compliance.
"""

admin_bp = Blueprint('admin_bp', __name__)


def require_client_login(f):
    """
    Decorator to ensure only logged in clients can access admin routes.
    """
    from functools import wraps

    """
    Chceks if the a valid client account is logged in ie the session has a client id
    If not then return the user to the client login page
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'client_id' not in session:
            flash("Please log in to access the audit dashboard.")
            return redirect(url_for('client_bp.client_login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@require_client_login
@audit_log('view', 'audit_logs')
def audit_dashboard():
    """
    Main audit dashboard showing recent logs and statistics.
    Filter settings limit what can be shown and allow the user
    to filter the data they want to see
    """
    # Get filter parameters
    page = request.args.get('page', 1, type=int)
    per_page = 25
    action_filter = request.args.get('action')
    actor_type_filter = request.args.get('actor_type')
    date_range = request.args.get('date_range', '7')  # days

    # Calculate date filter
    start_date = None
    if date_range and date_range != 'all':
        days = int(date_range)
        start_date = datetime.utcnow() - timedelta(days=days)

    # Get logs with pagination
    offset = (page - 1) * per_page
    logs = get_audit_logs(
        limit=per_page,
        offset=offset,
        action=action_filter if action_filter else None,
        actor_type=actor_type_filter if actor_type_filter else None,
        start_date=start_date
    )

    # Get total count for pagination
    total_count = get_audit_log_count(
        action=action_filter if action_filter else None,
        actor_type=actor_type_filter if actor_type_filter else None,
        start_date=start_date
    )

    total_pages = (total_count + per_page - 1) // per_page

    # Get action summary for stats
    action_summary = get_action_summary(start_date=start_date)

    # Verify chain integrity
    chain_valid = verify_audit_chain()

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
        client_username=session.get('client_username')
    )


@admin_bp.route('/export')
@require_client_login
@audit_log('export', 'audit_logs')
def export_audit_logs():
    """
    Export audit logs as CSV file.
    """
    # Get filter parameters
    action_filter = request.args.get('action')
    actor_type_filter = request.args.get('actor_type')
    date_range = request.args.get('date_range', '30')

    # Calculate date filter
    start_date = None
    if date_range and date_range != 'all':
        days = int(date_range)
        start_date = datetime.utcnow() - timedelta(days=days)

    # Get all matching logs (up to 10000)
    logs = get_audit_logs(
        limit=10000,
        action=action_filter if action_filter else None,
        actor_type=actor_type_filter if actor_type_filter else None,
        start_date=start_date
    )

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Log ID', 'Timestamp', 'Actor ID', 'Actor Type', 'Action',
        'Target Table', 'Target ID', 'IP Address', 'User Agent', 'Details'
    ])

    # Write data
    for log in logs:
        writer.writerow([
            log.get('log_id'),
            log.get('timestamp'),
            log.get('actor_id'),
            log.get('actor_type'),
            log.get('action'),
            log.get('target_table'),
            log.get('target_id'),
            log.get('ip_address'),
            log.get('user_agent'),
            log.get('details')
        ])

    # Create response
    output.seek(0)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=audit_logs_{timestamp}.csv'
        }
    )


@admin_bp.route('/verify-chain')
@require_client_login
@audit_log('view', 'audit_chain_verification')
def verify_chain():
    """
    Verify the integrity of the audit log hash chain.
    """
    is_valid = verify_audit_chain()

    if is_valid is None:
        flash("Error verifying audit chain. Database connection issue.", "error")
    elif is_valid:
        flash("Audit log chain integrity verified. No tampering detected.", "success")
    else:
        flash("WARNING: Audit log chain integrity check FAILED. Possible tampering detected!", "error")

    return redirect(url_for('admin_bp.audit_dashboard'))


@admin_bp.route('/init')
@require_client_login
def init_audit_table():
    """
    Initialize the audit logs table (first-time setup).
    """
    success = create_audit_table()

    if success:
        flash("Audit table created/verified successfully.", "success")
    else:
        flash("Error creating audit table. Check database connection.", "error")

    return redirect(url_for('admin_bp.audit_dashboard'))


@admin_bp.route('/geolocate/<ip>')
@require_client_login
def geolocate_ip(ip):
    """
    Returns geolocation data for a given IP address.
    Uses ip-api.com
    """
    try:
        api_url = f"http://ip-api.com/json/{ip}?fields=status,message,country,city,lat,lon,isp"
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