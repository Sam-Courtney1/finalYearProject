from functools import wraps
from flask import request, session
from data.audit_database import insert_audit_log

"""
Audit Service - Decorator and Helper Functions
GDPR Article 32 - Security of Processing

This module provides the @audit_log decorator for automatically logging
access to routes, plus helper functions for manual audit logging.

The decorator captures:
- Who performed the action (user/client ID from session)
- What action was performed
- When it happened (automatic timestamp)
- From where (IP address, user agent)
- What data was accessed (target table/ID)
"""


def get_client_ip():
    """
    Gets the real client IP address, handling proxies.
    """
    # Check for forwarded IP (when behind load balancer/proxy)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr


def get_actor_info():
    """
    Gets current actor (user or client) from session.
    Returns tuple of (actor_id, actor_type).
    """
    if 'user_id' in session:
        return session['user_id'], 'user'
    elif 'client_id' in session:
        return session['client_id'], 'client'
    elif 'pending_2fa_user' in session:
        return session['pending_2fa_user'], 'user'
    else:
        return None, 'anonymous'


def audit_log(action, target_table=None, get_target_id=None):
    """
    Decorator for automatically logging route access.

    Parameters:
    - action: The action being performed ('view', 'create', 'update', 'delete', 'export', 'login', 'logout')
    - target_table: The database table being accessed (optional)
    - get_target_id: Function to extract target_id from request/kwargs (optional)

    Usage:
        @app.route('/user/<int:user_id>')
        @audit_log('view', 'users', lambda **kw: kw.get('user_id'))
        def view_user(user_id):
            ...

        @app.route('/data')
        @audit_log('view', 'user_data')
        def view_data():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Get actor information
            actor_id, actor_type = get_actor_info()

            # Get target ID if function provided
            target_id = None
            if get_target_id:
                try:
                    target_id = get_target_id(**kwargs)
                except Exception:
                    pass

            # If no target_id function, try to get from session for user data
            if target_id is None and target_table == 'user_data':
                target_id = session.get('user_id')

            # Build details dict with request info
            details = {
                'endpoint': request.endpoint,
                'method': request.method,
                'path': request.path
            }

            # Add form data keys (not values for security) for POST requests
            if request.method == 'POST' and request.form:
                details['form_fields'] = list(request.form.keys())

            # Log the action
            insert_audit_log(
                actor_id=actor_id,
                actor_type=actor_type,
                action=action,
                target_table=target_table,
                target_id=target_id,
                ip_address=get_client_ip(),
                user_agent=request.headers.get('User-Agent'),
                details=details
            )

            # Execute the actual function
            return f(*args, **kwargs)
        return wrapper
    return decorator


def log_login_success(user_id, user_type='user'):
    """
    Logs a successful login event.
    """
    insert_audit_log(
        actor_id=user_id,
        actor_type=user_type,
        action='login',
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent'),
        details={'success': True}
    )


def log_login_failed(username, user_type='user'):
    """
    Logs a failed login attempt.
    """
    insert_audit_log(
        actor_id=None,
        actor_type=user_type,
        action='login_failed',
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent'),
        details={'attempted_username': username}
    )


def log_logout(user_id, user_type='user'):
    """
    Logs a logout event.
    """
    insert_audit_log(
        actor_id=user_id,
        actor_type=user_type,
        action='logout',
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent')
    )


def log_data_access(user_id, target_table, target_id=None, details=None):
    """
    Logs data access event.
    """
    actor_id, actor_type = get_actor_info()
    insert_audit_log(
        actor_id=actor_id,
        actor_type=actor_type,
        action='view',
        target_table=target_table,
        target_id=target_id,
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent'),
        details=details
    )


def log_data_create(target_table, target_id, details=None):
    """
    Logs data creation event.
    """
    actor_id, actor_type = get_actor_info()
    insert_audit_log(
        actor_id=actor_id,
        actor_type=actor_type,
        action='create',
        target_table=target_table,
        target_id=target_id,
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent'),
        details=details
    )


def log_data_update(target_table, target_id, details=None):
    """
    Logs data update event.
    """
    actor_id, actor_type = get_actor_info()
    insert_audit_log(
        actor_id=actor_id,
        actor_type=actor_type,
        action='update',
        target_table=target_table,
        target_id=target_id,
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent'),
        details=details
    )


def log_data_delete(target_table, target_id, details=None):
    """
    Logs data deletion event.
    """
    actor_id, actor_type = get_actor_info()
    insert_audit_log(
        actor_id=actor_id,
        actor_type=actor_type,
        action='delete',
        target_table=target_table,
        target_id=target_id,
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent'),
        details=details
    )


def log_data_export(user_id, export_format='json', details=None):
    """
    Logs data export event.
    """
    actor_id, actor_type = get_actor_info()
    export_details = {'format': export_format}
    if details:
        export_details.update(details)

    insert_audit_log(
        actor_id=actor_id,
        actor_type=actor_type,
        action='export',
        target_table='user_data',
        target_id=user_id,
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent'),
        details=export_details
    )