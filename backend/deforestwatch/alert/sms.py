"""Twilio SMS adapter with a safe disabled/dry-run default."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import get_settings


@dataclass(frozen=True)
class ProviderResult:
    status: str
    provider_id: str | None = None
    error: str | None = None


def send_sms(to: str, body: str, *, dry_run: bool | None = None) -> ProviderResult:
    settings = get_settings()
    if dry_run is None:
        dry_run = not settings.notifications_enabled
    if dry_run:
        return ProviderResult("skipped", error="notifications disabled")
    if not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_from_number:
        return ProviderResult("failed", error="Twilio credentials are not configured")
    try:
        from twilio.rest import Client
    except ImportError:
        return ProviderResult("failed", error="twilio package is not installed")
    try:
        message = Client(settings.twilio_account_sid, settings.twilio_auth_token).messages.create(
            body=body, from_=settings.twilio_from_number, to=to,
        )
        return ProviderResult("sent", provider_id=str(message.sid))
    except Exception as exc:
        return ProviderResult("failed", error=type(exc).__name__)
