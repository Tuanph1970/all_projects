"""Email delivery for auth flows.

Uses stdlib smtplib in a worker thread to keep the async path non-blocking.
If SMTP is not configured (SMTP_HOST unset) the email is logged instead —
this lets local development exercise the flow without a real mailserver.
"""
import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


def _build_message(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: Optional[str],
    from_email: str,
    from_name: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = formataddr((from_name, from_email))
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")
    return msg


def _send_sync(msg: EmailMessage) -> None:
    settings = get_settings()
    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        smtp.ehlo()
        if settings.SMTP_USE_TLS:
            smtp.starttls(context=context)
            smtp.ehlo()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(msg)


async def send_email(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
) -> bool:
    """Send an email. Returns True if the message was handed to the SMTP server,
    False if SMTP is not configured or the send failed.
    """
    settings = get_settings()
    if not settings.SMTP_HOST:
        logger.warning(
            "SMTP not configured (SMTP_HOST unset); email to %s skipped. Subject=%r",
            to_email,
            subject,
        )
        logger.info("Email body (would-be sent) to %s:\n%s", to_email, text_body)
        return False

    msg = _build_message(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        from_email=settings.SMTP_FROM_EMAIL,
        from_name=settings.SMTP_FROM_NAME,
    )
    try:
        await asyncio.to_thread(_send_sync, msg)
        logger.info("Sent email to %s subject=%r", to_email, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False


async def send_password_reset_email(*, to_email: str, reset_link: str, expires_minutes: int) -> bool:
    subject = "Đặt lại mật khẩu Stock Helper"
    text_body = (
        f"Xin chào,\n\n"
        f"Bạn vừa yêu cầu đặt lại mật khẩu cho tài khoản Stock Helper.\n"
        f"Vui lòng truy cập liên kết sau trong vòng {expires_minutes} phút:\n\n"
        f"{reset_link}\n\n"
        f"Nếu bạn không yêu cầu, hãy bỏ qua email này.\n"
    )
    html_body = (
        f"<p>Xin chào,</p>"
        f"<p>Bạn vừa yêu cầu đặt lại mật khẩu cho tài khoản <strong>Stock Helper</strong>.</p>"
        f"<p>Vui lòng nhấn vào liên kết sau trong vòng <strong>{expires_minutes} phút</strong>:</p>"
        f'<p><a href="{reset_link}">{reset_link}</a></p>'
        f"<p style=\"color:#666;font-size:12px\">Nếu bạn không yêu cầu, hãy bỏ qua email này.</p>"
    )
    return await send_email(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
