from dataclasses import dataclass

from .dedupe import AlertCandidate, dedupe


@dataclass
class AlertResult:
    alerts_created: int
    alerts_deduped: int
    sms_sent: int = 0
    emails_sent: int = 0
    failures: list[str] | None = None


def dispatch_alerts(candidates: list[AlertCandidate], existing: list[AlertCandidate], notifications_enabled: bool = False,
                    sms_sender=None, email_sender=None) -> AlertResult:
    accepted, deduped = dedupe(candidates, existing)
    # Provider calls are intentionally isolated for Phase 7 credentials; the
    # default development behavior records candidates without sending.
    if not notifications_enabled:
        failures = ["notifications disabled"]
    else:
        failures = []
        if sms_sender is None:
            failures.append("sms provider not configured")
        if email_sender is None:
            failures.append("email provider not configured")
    return AlertResult(alerts_created=len(accepted), alerts_deduped=deduped, failures=failures)
