"""SMTP email delivery for portfolio-service notifications.

Mirrors the auth-service email_service shape (stdlib smtplib in a worker
thread). Kept as a per-service copy rather than a stock-common helper
for now — second consumer of SMTP, but the surface is small and stable
enough that DRY-ing it up isn't pulling its weight yet (see CLAUDE.md
"three similar lines is better than a premature abstraction"). If a
third service starts sending email, lift this into stock-common.

If SMTP_HOST is unset the email is logged instead, mirroring the dev
fallback in auth-service so local development without a mailserver
still exercises the flow.
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
    """Send an email. Returns True if handed to the SMTP server, False if
    SMTP is unconfigured or the send failed."""
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


def format_alert_email(payload: dict) -> tuple[str, str, str]:
    """Build (subject, text_body, html_body) for an alert-triggered email.

    Mirrors notification_consumer._format_alert_triggered's title/body
    style so the email content matches what users see in the bell-icon
    dropdown.
    """
    symbol = payload.get("symbol", "?")
    alert_type = payload.get("alert_type", "")
    target_price = payload.get("target_price")
    target_percent = payload.get("target_percent")
    trigger_price = payload.get("trigger_price")

    if alert_type == "above":
        subject = f"[Stock Helper] {symbol} crossed above {target_price}"
        intro = (
            f"Your alert for {symbol} fired: price reached {trigger_price}, "
            f"hitting your above-{target_price} threshold."
        )
    elif alert_type == "below":
        subject = f"[Stock Helper] {symbol} dropped below {target_price}"
        intro = (
            f"Your alert for {symbol} fired: price dropped to {trigger_price}, "
            f"hitting your below-{target_price} threshold."
        )
    elif alert_type == "change_percent":
        subject = f"[Stock Helper] {symbol} moved {target_percent}%+"
        intro = (
            f"Your alert for {symbol} fired: price hit {trigger_price}, "
            f"a move greater than {target_percent}%."
        )
    else:
        subject = f"[Stock Helper] Alert triggered for {symbol}"
        intro = f"Your alert for {symbol} fired at {trigger_price}."

    text_body = (
        f"{intro}\n\n"
        f"You can review and manage alerts in the Stock Helper app.\n"
    )
    html_body = (
        f"<p>{intro}</p>"
        f"<p style=\"color:#666;font-size:12px\">"
        f"You can review and manage alerts in the Stock Helper app."
        f"</p>"
    )
    return subject, text_body, html_body
