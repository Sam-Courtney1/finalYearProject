import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def send_otp_email(to_email: str, otp_code: str) -> tuple[bool, str]:
    """
    Send a 6 digit OTP code to the users email address for 2FA login.
    Returns (success, error_message).
    """
    subject = "Your Login Verification Code"
    body_html = f"""
    <html><body>
    <p>Your verification code for the Organ Donation System is:</p>
    <h2 style="letter-spacing:4px;">{otp_code}</h2>
    <p>This code expires in <strong>10 minutes</strong>.</p>
    <p>If you did not attempt to log in, please ignore this email.</p>
    </body></html>
    """
    return _send_email(to_email, subject, body_html)


def send_password_reset_email(to_email: str, reset_url: str) -> tuple[bool, str]:
    """
    Send a password reset link to the users email address.
    Returns (success, error_message).
    """
    subject = "Reset Your Password"
    body_html = f"""
    <html><body>
    <p>You requested a password reset for the Organ Donation System.</p>
    <p><a href="{reset_url}" style="padding:10px 20px;background:#1a6b3c;color:#fff;
       text-decoration:none;border-radius:4px;">Reset My Password</a></p>
    <p>Or copy this link: {reset_url}</p>
    <p>This link expires in <strong>1 hour</strong>.</p>
    <p>If you did not request a reset, please ignore this email.</p>
    </body></html>
    """
    return _send_email(to_email, subject, body_html)


def _send_email(to_email: str, subject: str, body_html: str) -> tuple[bool, str]:
    """Returns (success, error_message). error_message is empty on success."""
    sender = os.getenv("SMTP_EMAIL", "")
    password = os.getenv("SMTP_PASSWORD", "")

    if not sender or not password:
        msg = (
            f"SMTP_EMAIL or SMTP_PASSWORD not set "
            f"SMTP_EMAIL={'set' if sender else 'MISSING'}, "
            f"SMTP_PASSWORD={'set' if password else 'MISSING'}"
        )
        logger.warning(msg)
        return False, msg

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, to_email, msg.as_string())

        return True, ""
    except Exception as e:
        error_msg = str(e)
        logger.error("Email send error: %s", error_msg)
        return False, error_msg
