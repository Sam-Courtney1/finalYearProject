from functools import wraps
from flask import request, session
from data.audit_database import insert_audit_log


def get_client_ip():
    """
    Gets the real client IP address
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


def get_audit_client_id(actor_type=None):
    """
    Determines the client_id for audit log tagging.
    Returns the client_id from session if the actor is a client,
    or None for user/anonymous actions (which are not client-specific).
    """
    if actor_type == 'client' and 'client_id' in session:
        return session['client_id']
    return None


def audit_log(action, target_table=None, get_target_id=None, get_client_id=None):
    """ Decorator for automatically logging route access."""

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

            # Determine client_id for this audit entry
            client_id = None
            if get_client_id:
                try:
                    client_id = get_client_id(**kwargs)
                except Exception:
                    pass
            if client_id is None:
                client_id = get_audit_client_id(actor_type)

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
                details=details,
                client_id=client_id
            )

            # Execute the actual function
            return f(*args, **kwargs)
        return wrapper
    return decorator


def log_login_success(user_id, user_type='user'):
    """
    Logs a successful login event.
    Client logins are tagged with client_id, user logins are not client specific.
    """
    client_id = user_id if user_type == 'client' else None
    insert_audit_log(
        actor_id=user_id,
        actor_type=user_type,
        action='login',
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent'),
        details={'success': True},
        client_id=client_id
    )


def log_login_failed(username, user_type='user'):
    """
    Logs a failed login attempt.
    """
    client_id = get_audit_client_id(user_type)
    insert_audit_log(
        actor_id=None,
        actor_type=user_type,
        action='login_failed',
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent'),
        details={'attempted_username': username},
        client_id=client_id
    ) 


def log_logout(user_id, user_type='user'):
    """
    Logs a logout event.
    """
    client_id = user_id if user_type == 'client' else None
    insert_audit_log(
        actor_id=user_id,
        actor_type=user_type,
        action='logout',
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent'),
        client_id=client_id
    )


def _log_data_event(action, target_table=None, target_id=None, details=None, client_id=None):
    """
    Shared helper for logging data events (view, create, update, delete, export).
    """
    actor_id, actor_type = get_actor_info()
    if client_id is None:
        client_id = get_audit_client_id(actor_type)
    insert_audit_log(
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        target_table=target_table,
        target_id=target_id,
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent'),
        details=details,
        client_id=client_id
    )


def log_data_access(user_id, target_table, target_id=None, details=None, client_id=None):
    _log_data_event('view', target_table, target_id, details, client_id)


def log_data_create(target_table, target_id, details=None, client_id=None):
    _log_data_event('create', target_table, target_id, details, client_id)


def log_data_update(target_table, target_id, details=None, client_id=None):
    _log_data_event('update', target_table, target_id, details, client_id)


def log_data_delete(target_table, target_id, details=None, client_id=None):
    _log_data_event('delete', target_table, target_id, details, client_id)


def log_data_export(user_id, export_format='json', details=None, client_id=None):
    export_details = {'format': export_format}
    if details:
        export_details.update(details)
    _log_data_event('export', 'user_data', user_id, export_details, client_id)
