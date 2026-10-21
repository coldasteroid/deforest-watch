from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    skipped_no_clear_scene = "skipped_no_clear_scene"


class AlertTier(str, Enum):
    watch = "watch"
    alert = "alert"
    critical = "critical"


class AlertStatus(str, Enum):
    new = "new"
    verified = "verified"
    false_positive = "false_positive"
    resolved = "resolved"


class Channel(str, Enum):
    sms = "sms"
    email = "email"


class DeliveryStatus(str, Enum):
    sent = "sent"
    failed = "failed"
    skipped = "skipped"


UUIDColumn = PGUUID(as_uuid=True)


class Aoi(Base):
    __tablename__ = "aoi"
    id: Mapped[UUID] = mapped_column(UUIDColumn, primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    geom: Mapped[object] = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    area_km2: Mapped[float] = mapped_column(Float, nullable=False)
    cadence_days: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    min_patch_ha: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    sensor: Mapped[str] = mapped_column(String, default="S2", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Run(Base):
    __tablename__ = "run"
    id: Mapped[UUID] = mapped_column(UUIDColumn, primary_key=True, default=uuid4)
    aoi_id: Mapped[UUID] = mapped_column(ForeignKey("aoi.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[RunStatus] = mapped_column(nullable=False, default=RunStatus.queued)
    trigger: Mapped[str] = mapped_column(String, default="schedule", nullable=False)
    kind: Mapped[str] = mapped_column(String, default="operational", nullable=False)
    sensor: Mapped[str] = mapped_column(String, default="S2", nullable=False)
    year: Mapped[int | None] = mapped_column(Integer)
    current_start: Mapped[object | None] = mapped_column(Date)
    current_end: Mapped[object | None] = mapped_column(Date)
    baseline_start: Mapped[object | None] = mapped_column(Date)
    baseline_end: Mapped[object | None] = mapped_column(Date)
    seasonal_start: Mapped[object | None] = mapped_column(Date)
    seasonal_end: Mapped[object | None] = mapped_column(Date)
    model_version: Mapped[str | None] = mapped_column(String)
    chips_total: Mapped[int | None] = mapped_column(Integer)
    chips_gated_in: Mapped[int | None] = mapped_column(Integer)
    detections_count: Mapped[int | None] = mapped_column(Integer)
    alerts_created: Mapped[int | None] = mapped_column(Integer)
    alerts_deduped: Mapped[int | None] = mapped_column(Integer)
    overlay_path: Mapped[str | None] = mapped_column(Text)
    ndvi_diff_path: Mapped[str | None] = mapped_column(Text)
    loss_mask_path: Mapped[str | None] = mapped_column(Text)
    overlay_bounds: Mapped[list[float] | None] = mapped_column(ARRAY(Float))
    cloud_pct_mean: Mapped[float | None] = mapped_column(Float)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_s: Mapped[float | None] = mapped_column(Float)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Scene(Base):
    __tablename__ = "scene"
    id: Mapped[UUID] = mapped_column(UUIDColumn, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("run.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    sensor: Mapped[str] = mapped_column(String, nullable=False)
    scene_ids: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    cloud_pct: Mapped[float | None] = mapped_column(Float)
    window_start: Mapped[object] = mapped_column(Date, nullable=False)
    window_end: Mapped[object] = mapped_column(Date, nullable=False)
    tif_path: Mapped[str] = mapped_column(Text, nullable=False)
    from_cache: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Chip(Base):
    __tablename__ = "chip"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("run.id", ondelete="CASCADE"), nullable=False)
    row_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    col_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    geom: Mapped[object] = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    ndvi_drop_mean: Mapped[float | None] = mapped_column(Float)
    ndvi_drop_pixels: Mapped[int | None] = mapped_column(Integer)
    forest_pixels: Mapped[int | None] = mapped_column(Integer)
    gated_in: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mean_prob: Mapped[float | None] = mapped_column(Float)


class Detection(Base):
    __tablename__ = "detection"
    id: Mapped[UUID] = mapped_column(UUIDColumn, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("run.id", ondelete="CASCADE"), nullable=False)
    aoi_id: Mapped[UUID] = mapped_column(ForeignKey("aoi.id", ondelete="CASCADE"), nullable=False)
    geom: Mapped[object] = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    area_ha: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    ndvi_drop_mean: Mapped[float] = mapped_column(Float, nullable=False)
    centroid: Mapped[object] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    tier: Mapped[AlertTier] = mapped_column(nullable=False)
    chip_ids: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Alert(Base):
    __tablename__ = "alert"
    id: Mapped[UUID] = mapped_column(UUIDColumn, primary_key=True, default=uuid4)
    aoi_id: Mapped[UUID] = mapped_column(ForeignKey("aoi.id", ondelete="CASCADE"), nullable=False)
    first_run_id: Mapped[UUID] = mapped_column(ForeignKey("run.id"), nullable=False)
    last_seen_run_id: Mapped[UUID] = mapped_column(ForeignKey("run.id"), nullable=False)
    detection_id: Mapped[UUID | None] = mapped_column(ForeignKey("detection.id"))
    geom: Mapped[object] = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    centroid: Mapped[object] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    area_ha: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    ndvi_drop_mean: Mapped[float] = mapped_column(Float, nullable=False)
    tier: Mapped[AlertTier] = mapped_column(nullable=False)
    status: Mapped[AlertStatus] = mapped_column(nullable=False, default=AlertStatus.new)
    times_seen: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    thumbnail_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Subscriber(Base):
    __tablename__ = "subscriber"
    id: Mapped[UUID] = mapped_column(UUIDColumn, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone_e164: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    role: Mapped[str | None] = mapped_column(String)
    min_tier: Mapped[AlertTier] = mapped_column(nullable=False, default=AlertTier.alert)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AoiSubscriber(Base):
    __tablename__ = "aoi_subscriber"
    aoi_id: Mapped[UUID] = mapped_column(ForeignKey("aoi.id", ondelete="CASCADE"), primary_key=True)
    subscriber_id: Mapped[UUID] = mapped_column(ForeignKey("subscriber.id", ondelete="CASCADE"), primary_key=True)


class AlertDelivery(Base):
    __tablename__ = "alert_delivery"
    id: Mapped[UUID] = mapped_column(UUIDColumn, primary_key=True, default=uuid4)
    alert_id: Mapped[UUID] = mapped_column(ForeignKey("alert.id", ondelete="CASCADE"), nullable=False)
    subscriber_id: Mapped[UUID] = mapped_column(ForeignKey("subscriber.id", ondelete="CASCADE"), nullable=False)
    channel: Mapped[Channel] = mapped_column(nullable=False)
    status: Mapped[DeliveryStatus] = mapped_column(nullable=False)
    provider_id: Mapped[str | None] = mapped_column(String)
    error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[UUID] = mapped_column(UUIDColumn, primary_key=True, default=uuid4)
    alert_id: Mapped[UUID] = mapped_column(ForeignKey("alert.id", ondelete="CASCADE"), nullable=False)
    verdict: Mapped[AlertStatus] = mapped_column(nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String)
    used_in_model: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ModelVersion(Base):
    __tablename__ = "model_version"
    version: Mapped[str] = mapped_column(String, primary_key=True)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    in_channels: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[str] = mapped_column(String, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    train_samples: Mapped[int | None] = mapped_column(Integer)
    metrics: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class SdgSnapshot(Base):
    __tablename__ = "sdg_snapshot"
    id: Mapped[UUID] = mapped_column(UUIDColumn, primary_key=True, default=uuid4)
    aoi_id: Mapped[UUID | None] = mapped_column(ForeignKey("aoi.id", ondelete="CASCADE"))
    hectares_detected: Mapped[float] = mapped_column(Float, nullable=False)
    co2e_tonnes: Mapped[float] = mapped_column(Float, nullable=False)
    percent_of_aoi: Mapped[float | None] = mapped_column(Float)
    alerts_total: Mapped[int] = mapped_column(Integer, nullable=False)
    alerts_sent: Mapped[int] = mapped_column(Integer, nullable=False)
    verified: Mapped[int] = mapped_column(Integer, nullable=False)
    false_positive: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


Index("aoi_geom_gix", Aoi.geom, postgresql_using="gist")
Index("run_aoi_created_idx", Run.aoi_id, Run.created_at.desc())
Index("run_annual_idx", Run.aoi_id, Run.kind, Run.year, postgresql_where=(Run.kind == "annual"))
Index("chip_run_idx", Chip.run_id)
Index("chip_geom_gix", Chip.geom, postgresql_using="gist")
Index("detection_geom_gix", Detection.geom, postgresql_using="gist")
Index("detection_run_idx", Detection.run_id)
Index("alert_geom_gix", Alert.geom, postgresql_using="gist")
Index("alert_aoi_status_idx", Alert.aoi_id, Alert.status, Alert.detected_at.desc())
