"""Email service for signup approval notifications."""
from __future__ import annotations

from email.message import EmailMessage

from app.config import settings
from app.security.jwt_auth import create_access_token
from app.utils.logging import get_logger

log = get_logger("services.email")


def _admin_email() -> str:
    return settings.admin_email or settings.contact_email


async def send_approval_email(user: dict) -> None:
    """Send approval request email to admin with approve/reject links."""
    admin_addr = _admin_email()
    if not admin_addr:
        log.warning("no_admin_email_configured")
        return

    approval_token = create_access_token(
        {"sub": user["id"], "purpose": "approval", "action": "approve"},
    )
    reject_token = create_access_token(
        {"sub": user["id"], "purpose": "approval", "action": "reject"},
    )

    approve_url = f"{settings.frontend_url}/admin/approve?token={approval_token}"
    reject_url = f"{settings.frontend_url}/admin/approve?token={reject_token}&action=reject"

    body = f"""New signup request for Context-Aware AI Assistant:

Username: {user['username']}
Email: {user['email']}
Signed up: {user.get('created_at', 'just now')}

Approve (assign role & permissions):
{approve_url}

Reject:
{reject_url}

— ContextAI
"""

    if not settings.smtp_user or not settings.smtp_password:
        log.warning("smtp_not_configured_logging_approval", user=user["username"], approve_url=approve_url)
        log.info("approval_link", url=approve_url)
        return

    try:
        import aiosmtplib

        msg = EmailMessage()
        msg["From"] = settings.smtp_user
        msg["To"] = admin_addr
        msg["Subject"] = f"[ContextAI] New signup: {user['username']}"
        msg.set_content(body)

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        log.info("approval_email_sent", to=admin_addr, user=user["username"])
    except Exception as e:
        log.error("approval_email_failed", error=str(e), to=admin_addr)


async def send_user_notification(user: dict, approved: bool, reason: str = "") -> None:
    """Notify user of approval/rejection."""
    if not settings.smtp_user or not settings.smtp_password:
        log.warning("smtp_not_configured_skipping_notification", user=user["username"])
        return

    subject = f"[ContextAI] Your account has been {'approved' if approved else 'denied'}"
    if approved:
        body = f"Hi {user['username']},\n\nYour account has been approved! You can now log in at:\n{settings.frontend_url}/login\n\nRole: {user.get('role', 'member')}\n\n— ContextAI"
    else:
        body = f"Hi {user['username']},\n\nYour signup request has been denied.\n{f'Reason: {reason}' if reason else ''}\n\n— ContextAI"

    try:
        import aiosmtplib

        msg = EmailMessage()
        msg["From"] = settings.smtp_user
        msg["To"] = user["email"]
        msg["Subject"] = subject
        msg.set_content(body)

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        log.info("user_notification_sent", to=user["email"], approved=approved)
    except Exception as e:
        log.error("user_notification_failed", error=str(e), to=user["email"])
