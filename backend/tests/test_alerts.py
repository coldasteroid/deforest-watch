from datetime import datetime, timezone

from shapely.geometry import box

from deforestwatch.alert.dedupe import AlertCandidate, dedupe, tier_for
from deforestwatch.alert.dispatch import dispatch_alerts
from deforestwatch.alert.templates import render_sms
from deforestwatch.alert.feedback import append_feedback_export
from deforestwatch.alert.sms import send_sms
from deforestwatch.alert.email import send_email


def candidate(x: float) -> AlertCandidate:
    return AlertCandidate(box(x, 0, x + 1, 1), 2, 0.9, 0.4, datetime.now(timezone.utc), "alert")


def test_tiers_dedupe_and_sms_limit():
    assert tier_for(0.5) == "watch"
    assert tier_for(1) == "alert"
    assert tier_for(10) == "critical"
    accepted, count = dedupe([candidate(0)], [candidate(0)])
    assert not accepted and count == 1
    result = dispatch_alerts([candidate(2)], [], notifications_enabled=False)
    assert result.alerts_created == 1 and result.sms_sent == 0
    enabled_without_providers = dispatch_alerts([candidate(3)], [], notifications_enabled=True)
    assert enabled_without_providers.failures == ["sms provider not configured", "email provider not configured"]
    assert len(render_sms("PEKB Block", 12.3, "critical", "http://localhost:3000/alerts/1")) <= 160


def test_feedback_export_is_append_only_jsonl(tmp_path):
    path = tmp_path / "feedback.jsonl"
    append_feedback_export(path, "alert-1", "verified", "visited", "Aditya")
    append_feedback_export(path, "alert-2", "false_positive", None, "Reviewer")
    rows = [__import__("json").loads(line) for line in path.read_text().splitlines()]
    assert [row["alert_id"] for row in rows] == ["alert-1", "alert-2"]


def test_provider_adapters_are_disabled_without_sending(monkeypatch):
    monkeypatch.setenv("NOTIFICATIONS_ENABLED", "false")
    from deforestwatch.config import get_settings
    get_settings.cache_clear()
    assert send_sms("+91XXXXXXXXXX", "test").status == "skipped"
    assert send_email("test@example.com", "test", "test").status == "skipped"
    get_settings.cache_clear()
