import json
from datetime import date
from pathlib import Path
from uuid import uuid4

import typer

from .contracts import DateWindow, DetectRequest, FetchRequest, PreprocessRequest
from .db.base import Base, engine

app = typer.Typer(help="DeforestWatch command-line tools")


@app.command()
def db_upgrade() -> None:
    """Create the configured database tables during local development."""
    from .db import models  # noqa: F401

    Base.metadata.create_all(engine)
    typer.echo("database tables created")


@app.command()
def seed() -> None:
    """Seed the checked-in AOIs and the configured team subscriber."""
    from scripts.seed_aois import seed as seed_aois
    from scripts.seed_subscribers import seed as seed_subscribers

    typer.echo(f"seeded {seed_aois()} AOIs and {seed_subscribers()} subscribers")


def _aoi_feature(slug: str) -> dict:
    path = Path(__file__).resolve().parents[2] / "data" / "aoi" / "seed_aois.geojson"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for feature in payload["features"]:
        if feature.get("properties", {}).get("slug") == slug:
            return feature
    raise typer.BadParameter(f"unknown AOI: {slug}")


def _window(value: str) -> DateWindow:
    end = date.fromisoformat(value)
    return DateWindow(start=end.replace(day=max(1, end.day - 14)), end=end)


@app.command()
def fetch(aoi: str = typer.Option(..., "--aoi"), date_value: str = typer.Option(..., "--date"), sensor: str = typer.Option("S2", "--sensor")) -> None:
    """Fetch imagery from the configured GEE or fixture backend."""
    end = date.fromisoformat(date_value)
    current = _window(date_value)
    recent_end = end.replace(year=end.year - 1)
    seasonal_end = end.replace(year=end.year - 2)
    req = FetchRequest(run_id=uuid4(), aoi_id=uuid4(), aoi_geojson=_aoi_feature(aoi),
                       current=current,
                       baseline_recent=_window(recent_end.isoformat()),
                       baseline_seasonal=_window(seasonal_end.isoformat()), sensor=sensor)
    from .ingest import fetch_imagery
    result = fetch_imagery(req)
    typer.echo(result.model_dump_json(indent=2))


@app.command()
def detect(aoi: str = typer.Option(..., "--aoi"), date_value: str = typer.Option(..., "--date"), model: str = typer.Option("none", "--model")) -> None:
    """Run the baseline detector through the configured imagery backend."""
    end = date.fromisoformat(date_value)
    current = _window(date_value)
    req = FetchRequest(run_id=uuid4(), aoi_id=uuid4(), aoi_geojson=_aoi_feature(aoi),
                       current=current,
                       baseline_recent=_window(end.replace(year=end.year - 1).isoformat()),
                       baseline_seasonal=_window(end.replace(year=end.year - 2).isoformat()))
    from .detect.baseline_ndvi import detect as run_detector
    from .ingest import fetch_imagery
    from .preprocess.run import preprocess
    fetch_result = fetch_imagery(req)
    pre = preprocess(PreprocessRequest(run_id=req.run_id, fetch=fetch_result))
    result = run_detector(DetectRequest(run_id=req.run_id, pre=pre))
    typer.echo(json.dumps({"run_id": str(req.run_id), "detections": len(result.detections),
                           "overlay": str(result.overlay_png), "loss_mask": str(result.loss_mask_tif)}))


@app.command("alert-test")
def alert_test(
    to: str = typer.Option(..., "--to", help="SMS recipient for the provider test"),
    email: str | None = typer.Option(None, "--email", help="Email recipient for the provider test"),
) -> None:
    """Render an alert test and report provider readiness without sending by default."""
    from .alert.templates import render_email_subject, render_sms
    from .config import get_settings

    settings = get_settings()
    payload = {
        "sms_recipient": to,
        "email_recipient": email,
        "sms_preview": render_sms("PEKB Block", 1.0, "alert", f"{settings.frontend_url}/alerts"),
        "email_subject": render_email_subject("PEKB Block", "alert"),
        "notifications_enabled": settings.notifications_enabled,
        "status": "provider_send_not_attempted" if not settings.notifications_enabled else "provider_adapters_required",
    }
    typer.echo(json.dumps(payload, indent=2))


if __name__ == "__main__":
    app()
