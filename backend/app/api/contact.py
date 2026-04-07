"""Contact form endpoint — sends email to configured recipient."""
from __future__ import annotations

from email.message import EmailMessage

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.utils.errors import AppError
from app.utils.logging import get_logger

router = APIRouter(tags=["contact"])
log = get_logger("contact")


class ContactRequest(BaseModel):
    name: str
    email: str
    subject: str
    body: str


@router.post("/api/contact")
async def send_contact_email(req: ContactRequest) -> dict:
    if not settings.smtp_user or not settings.smtp_password:
        log.warning("SMTP not configured, logging contact form instead")
        log.info(
            "contact_form",
            name=req.name,
            email=req.email,
            subject=req.subject,
            body=req.body[:200],
        )
        return {"success": True, "note": "Message received (email delivery pending SMTP config)"}

    try:
        import aiosmtplib

        msg = EmailMessage()
        msg["From"] = settings.smtp_user
        msg["To"] = settings.contact_email
        msg["Subject"] = f"[ContextAI Contact] {req.subject}"
        msg["Reply-To"] = req.email
        msg.set_content(
            f"From: {req.name} <{req.email}>\n\n{req.body}"
        )

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        log.info("contact_email_sent", to=settings.contact_email, from_email=req.email)
        return {"success": True}

    except Exception as e:
        log.error("contact_email_failed", error=str(e))
        raise AppError("Failed to send email. Please try again later.", status_code=500)
