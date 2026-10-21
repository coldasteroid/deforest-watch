"""SMTP email adapter with a safe disabled/dry-run default."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from ..config import get_settings


@dataclass(frozen=True)
class ProviderResult:
    status: str
    provider_id: str | None = None
    error: str | None = None


def send_email(to: str, subject: str, body: str, *, dry_run: bool | None = None) -> ProviderResult:
    settings = get_settings()
    if dry_run is None:
        dry_run = not settings.notifications_enabled
    if dry_run:
        return ProviderResult("skipped", error="notifications disabled")
    if not settings.smtp_user or not settings.smtp_password or not settings.smtp_from:
        return ProviderResult("failed", error="SMTP credentials are not configured")
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = settings.smtp_from, to, subject
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
        return ProviderResult("sent")
    except Exception as exc:
        return ProviderResult("failed", error=type(exc).__name__)
