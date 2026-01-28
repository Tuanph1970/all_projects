"""
Email Service for sending emails via SMTP
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP"""

    @staticmethod
    def _get_smtp_connection():
        """Create SMTP connection based on configuration"""
        if not settings.SMTP_SERVER:
            logger.warning("SMTP server not configured")
            return None

        try:
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            server.starttls()

            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

            return server
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {e}")
            return None

    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None
    ) -> bool:
        """
        Send an email to the specified address

        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML body content
            body_text: Plain text body (optional, will strip HTML if not provided)

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not settings.SMTP_SERVER:
            # Log for development - print email content
            logger.info(f"[DEV MODE] Email would be sent to: {to_email}")
            logger.info(f"[DEV MODE] Subject: {subject}")
            logger.info(f"[DEV MODE] Body: {body_text or body_html}")
            print(f"\n{'='*50}")
            print(f"📧 EMAIL TO: {to_email}")
            print(f"📧 SUBJECT: {subject}")
            print(f"📧 BODY:\n{body_text or body_html}")
            print(f"{'='*50}\n")
            return True

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg['To'] = to_email

            # Add text part
            if body_text:
                text_part = MIMEText(body_text, 'plain')
                msg.attach(text_part)

            # Add HTML part
            html_part = MIMEText(body_html, 'html')
            msg.attach(html_part)

            # Send email
            server = EmailService._get_smtp_connection()
            if server:
                server.sendmail(
                    settings.SMTP_FROM_EMAIL,
                    to_email,
                    msg.as_string()
                )
                server.quit()
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error("Failed to establish SMTP connection")
                return False

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    @staticmethod
    def send_temporary_password_email(
        to_email: str,
        temporary_password: str,
        expiry_hours: int = 5
    ) -> bool:
        """
        Send temporary password email to user

        Args:
            to_email: User's email address
            temporary_password: The generated temporary password
            expiry_hours: Number of hours the password is valid

        Returns:
            True if email was sent successfully
        """
        subject = "Ceramic Marketplace - Your Temporary Password"

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4A90A4; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
                .password-box {{ background-color: #fff; border: 2px dashed #4A90A4; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px; }}
                .password {{ font-size: 24px; font-weight: bold; color: #4A90A4; letter-spacing: 2px; }}
                .warning {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏺 Ceramic Marketplace</h1>
                </div>
                <div class="content">
                    <h2>Password Reset Request</h2>
                    <p>Hello,</p>
                    <p>We received a request to reset your password. Here is your temporary password:</p>

                    <div class="password-box">
                        <p style="margin: 0; color: #666;">Your Temporary Password</p>
                        <p class="password">{temporary_password}</p>
                    </div>

                    <div class="warning">
                        <strong>⚠️ Important:</strong>
                        <ul style="margin: 10px 0;">
                            <li>This password is only valid for <strong>{expiry_hours} hours</strong></li>
                            <li>Please login and change your password immediately after signing in</li>
                            <li>If you did not request this password reset, please ignore this email</li>
                        </ul>
                    </div>

                    <p>For security reasons, we recommend changing this temporary password to a strong, unique password as soon as possible.</p>

                    <p>Best regards,<br>The Ceramic Marketplace Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>© 2025 Ceramic Marketplace. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        body_text = f"""
Ceramic Marketplace - Password Reset

Hello,

We received a request to reset your password.

Your Temporary Password: {temporary_password}

⚠️ IMPORTANT:
- This password is only valid for {expiry_hours} hours
- Please login and change your password immediately after signing in
- If you did not request this password reset, please ignore this email

For security reasons, we recommend changing this temporary password to a strong, unique password as soon as possible.

Best regards,
The Ceramic Marketplace Team

---
This is an automated message. Please do not reply to this email.
© 2025 Ceramic Marketplace. All rights reserved.
        """

        return EmailService.send_email(to_email, subject, body_html, body_text)

    @staticmethod
    def send_verification_email(to_email: str, verification_token: str) -> bool:
        """
        Send email verification link to user

        Args:
            to_email: User's email address
            verification_token: The verification token

        Returns:
            True if email was sent successfully
        """
        subject = "Ceramic Marketplace - Verify Your Email"

        # TODO: Replace with actual frontend verification URL
        verification_url = f"https://ceramic-marketplace.com/verify-email?token={verification_token}"

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4A90A4; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; background-color: #4A90A4; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏺 Ceramic Marketplace</h1>
                </div>
                <div class="content">
                    <h2>Verify Your Email Address</h2>
                    <p>Hello,</p>
                    <p>Thank you for registering with Ceramic Marketplace! Please verify your email address to complete your registration.</p>

                    <p style="text-align: center;">
                        <a href="{verification_url}" class="button">Verify Email</a>
                    </p>

                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #4A90A4;">{verification_url}</p>

                    <p>This link will expire in 24 hours.</p>

                    <p>If you did not create an account, please ignore this email.</p>

                    <p>Best regards,<br>The Ceramic Marketplace Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>© 2025 Ceramic Marketplace. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        body_text = f"""
Ceramic Marketplace - Verify Your Email

Hello,

Thank you for registering with Ceramic Marketplace! Please verify your email address to complete your registration.

Click the link below to verify your email:
{verification_url}

This link will expire in 24 hours.

If you did not create an account, please ignore this email.

Best regards,
The Ceramic Marketplace Team

---
This is an automated message. Please do not reply to this email.
© 2025 Ceramic Marketplace. All rights reserved.
        """

        return EmailService.send_email(to_email, subject, body_html, body_text)
