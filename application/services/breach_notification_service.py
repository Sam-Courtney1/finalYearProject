from data.breach_database import get_breach_by_id
from data.breach_notification_database import (
    insert_breach_notification, update_notification_status,
    get_all_user_emails
)
from application.services.email_service import _send_email
import logging

logger = logging.getLogger(__name__)


def _mask_email(email):
    """
    Mask an email for storage
    Stores only enough to confirm the recipient without exposing the full address.
    """
    try:
        local, domain = email.rsplit('@', 1)
        masked_local = local[0] + '***' if len(local) > 1 else '***'
        return f"{masked_local}@{domain}"
    except (ValueError, IndexError):
        return '***@***'


"""
Sends email notifications to affected users when a data breach occurs.
Uses Gmail SMTP via the existing _send_email helper in email_service.py.
"""


def send_breach_notification_email(to_email, breach_title, description,
                                   data_types, remedial_actions, contact_email):
    """
    Send a breach notification email to a single user.
    Returns (success, error_message).
    """
    subject = f"Important: Data Breach Notification - {breach_title}"
    body_html = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: #dc3545; color: white; padding: 15px; border-radius: 4px 4px 0 0;">
            <h2 style="margin: 0;">Data Breach Notification</h2>
        </div>
        <div style="border: 1px solid #ddd; padding: 20px; border-radius: 0 0 4px 4px;">
            <p>We are writing to inform you of a data breach that may affect your personal
            data held by the Organ Donation System.</p>

            <h3 style="color: #dc3545;">What Happened</h3>
            <p><strong>{breach_title}</strong></p>
            <p>{description or 'Details are currently being investigated.'}</p>

            <h3 style="color: #dc3545;">What Data Was Affected</h3>
            <p>{data_types or 'The types of data affected are being assessed.'}</p>

            <h3 style="color: #dc3545;">What We Are Doing</h3>
            <p>{remedial_actions or 'We are actively investigating and taking steps to address this incident.'}</p>

            <h3 style="color: #dc3545;">What You Can Do</h3>
            <ul>
                <li>Review your account for any suspicious activity</li>
                <li>Consider changing your password</li>
                <li>You can exercise your GDPR rights at any time by logging into your account</li>
            </ul>

            <h3 style="color: #dc3545;">Contact Us</h3>
            <p>If you have questions about this incident, please contact our Data Protection Officer at:
               <a href="mailto:{contact_email}">{contact_email}</a></p>
        </div>
    </div>
    </body></html>
    """
    return _send_email(to_email, subject, body_html)


def notify_all_affected_users(breach_id, contact_email='organdonationfyp@gmail.com'):
    """
    Send breach notification emails to all users with an email on file.
    Returns summary dict: {total, sent, failed}.
    """
    breach = get_breach_by_id(breach_id)
    if not breach:
        logger.error("Breach %s not found", breach_id)
        return {'total': 0, 'sent': 0, 'failed': 0}

    user_emails = get_all_user_emails()
    if not user_emails:
        logger.warning("No user emails found for breach notification")
        return {'total': 0, 'sent': 0, 'failed': 0}

    sent_count = 0
    failed_count = 0

    for user_id, email in user_emails:
        # Store masked email in the notification record (GDPR data minimisation)
        notif_id = insert_breach_notification(breach_id, user_id, _mask_email(email))
        if not notif_id:
            failed_count += 1
            continue

        # Send the email
        success, error = send_breach_notification_email(
            to_email=email,
            breach_title=breach['title'],
            description=breach.get('description', ''),
            data_types=breach.get('data_types_affected', ''),
            remedial_actions=breach.get('remedial_actions', ''),
            contact_email=contact_email
        )

        if success:
            update_notification_status(notif_id, 'sent')
            sent_count += 1
        else:
            update_notification_status(notif_id, 'failed', error)
            failed_count += 1

    total = len(user_emails)
    logger.info("Breach #%s notification: %d sent, %d failed out of %d",
                breach_id, sent_count, failed_count, total)

    return {'total': total, 'sent': sent_count, 'failed': failed_count}
