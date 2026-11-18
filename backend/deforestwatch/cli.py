import json
from datetime import date, timedelta
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


def _window(value: str, days: int = 14) -> DateWindow:
    """A `days`-long window ending on `value`.

    This used to be `end.replace(day=max(1, end.day - days))`, which cannot
    cross a month boundary: asking for 5 November gave a four-day window
    starting on the 1st, and any date in the first fortnight of a month was
    silently truncated. A live Landsat 9 fetch failed on exactly that, since
    its 16-day revisit rarely puts a scene inside four days.
    """
    end = date.fromisoformat(value)
    return DateWindow(start=end - timedelta(days=days), end=end)


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


def _checkpoint_threshold(path: Path) -> float | None:
    """The decision threshold a checkpoint was selected at, if it records one."""
    try:
        import torch

        meta = torch.load(path, map_location="cpu", weights_only=False).get("meta", {})
        value = meta.get("best_val_threshold")
        return float(value) if value is not None else None
    except Exception:  # noqa: BLE001 - an unreadable meta block is not fatal
        return None


@app.command()
def detect(aoi: str = typer.Option(..., "--aoi"), date_value: str = typer.Option(..., "--date"),
           model: str = typer.Option("none", "--model"),
           threshold: float = typer.Option(None, "--threshold",
                                           help="override the detection probability threshold")) -> None:
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
    # --model was accepted and then dropped, so every run silently used the
    # NDVI baseline whatever was asked for. "none" keeps that baseline; any
    # other value is a checkpoint path and must exist, rather than falling
    # back to the baseline and reporting the result as if the model had run.
    detect_request = DetectRequest(run_id=req.run_id, pre=pre)
    if model != "none":
        checkpoint = Path(model)
        if not checkpoint.is_file():
            raise typer.BadParameter(f"checkpoint not found: {checkpoint}", param_hint="--model")
        update: dict = {"model_path": checkpoint}
        # A segmentation head trained on a fraction of a per cent of positive
        # pixels is not calibrated around 0.5, and training records the
        # threshold the checkpoint was selected at. Using the contract default
        # instead would score the model at an operating point it was never
        # chosen for. --threshold still overrides.
        if threshold is None:
            stored = _checkpoint_threshold(checkpoint)
            if stored is not None:
                update["prob_threshold"] = stored
                typer.echo(f"using checkpoint threshold {stored}", err=True)
        else:
            update["prob_threshold"] = threshold
        detect_request = detect_request.model_copy(update=update)
    elif threshold is not None:
        detect_request = detect_request.model_copy(update={"prob_threshold": threshold})
    result = run_detector(detect_request)
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
