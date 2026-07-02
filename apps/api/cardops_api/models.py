from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class SettingsRecord(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    demo_mode: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    local_only_mode: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cloud_ai_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    live_ebay_publishing_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    physical_file_moves_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    listing_export_mode: Mapped[str] = mapped_column(String(40), default="file_upload", nullable=False)
    ebay_direct_listing_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ebay_marketplace_id: Mapped[str] = mapped_column(String(40), default="EBAY_US", nullable=False)
    ebay_merchant_location_key: Mapped[str | None] = mapped_column(String(120))
    ebay_payment_policy_id: Mapped[str | None] = mapped_column(String(120))
    ebay_return_policy_id: Mapped[str | None] = mapped_column(String(120))
    ebay_fulfillment_policy_id: Mapped[str | None] = mapped_column(String(120))
    ebay_sync_limit: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    ebay_sync_offset: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ebay_sync_include_offers: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_listing_format: Mapped[str] = mapped_column(String(40), default="fixed_price", nullable=False)
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.72, nullable=False)
    tesseract_cmd: Mapped[str | None] = mapped_column(Text)
    ocr_language: Mapped[str] = mapped_column(String(40), default="eng", nullable=False)
    default_input_dir: Mapped[str | None] = mapped_column(Text)
    default_output_dir: Mapped[str | None] = mapped_column(Text)
    default_inventory_path: Mapped[str | None] = mapped_column(Text)
    default_ebay_export_path: Mapped[str | None] = mapped_column(Text)
    daily_ai_request_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_ai_cost_limit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DirectoryRoot(Base):
    __tablename__ = "directory_roots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    normalized_path_key: Mapped[str | None] = mapped_column(String(1024), index=True)
    label: Mapped[str | None] = mapped_column(String(200))
    recursive: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    exclude_patterns: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    allow_symlinks: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    images: Mapped[list[ImageAsset]] = relationship(back_populates="directory")


class FileOperationManifest(Base):
    __tablename__ = "file_operation_manifests"
    __table_args__ = (Index("ix_file_operation_manifests_type_status", "operation_type", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    operation_type: Mapped[str] = mapped_column(String(80), nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="planned", nullable=False)
    source_root_id: Mapped[str | None] = mapped_column(ForeignKey("directory_roots.id"), index=True)
    confirmation_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    collision_policy: Mapped[str] = mapped_column(String(40), default="skip", nullable=False)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    entries: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class CardInstance(Base):
    __tablename__ = "card_instances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    internal_sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    sport: Mapped[str | None] = mapped_column(String(80), index=True)
    player: Mapped[str | None] = mapped_column(String(200), index=True)
    team: Mapped[str | None] = mapped_column(String(160), index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(160), index=True)
    brand: Mapped[str | None] = mapped_column(String(160))
    set_name: Mapped[str | None] = mapped_column(String(240), index=True)
    set_year: Mapped[int | None] = mapped_column(Integer, index=True)
    card_number: Mapped[str | None] = mapped_column(String(80), index=True)
    subset: Mapped[str | None] = mapped_column(String(160))
    variation: Mapped[str | None] = mapped_column(String(160))
    parallel: Mapped[str | None] = mapped_column(String(160))
    rookie: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    autograph: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    relic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    serial_number_current: Mapped[int | None] = mapped_column(Integer)
    serial_number_total: Mapped[int | None] = mapped_column(Integer)
    raw_or_graded: Mapped[str] = mapped_column(String(40), default="raw", nullable=False)
    grading_company: Mapped[str | None] = mapped_column(String(80))
    grade: Mapped[str | None] = mapped_column(String(40))
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    condition_notes: Mapped[str | None] = mapped_column(Text)
    acquisition_cost: Mapped[float | None] = mapped_column(Numeric(10, 2))
    estimated_value: Mapped[float | None] = mapped_column(Numeric(10, 2))
    verified_sale_low: Mapped[float | None] = mapped_column(Numeric(10, 2))
    verified_sale_high: Mapped[float | None] = mapped_column(Numeric(10, 2))
    storage_location: Mapped[str | None] = mapped_column(String(160), index=True)
    current_lot_assignment: Mapped[str | None] = mapped_column(String(120), index=True)
    current_ebay_listing: Mapped[str | None] = mapped_column(String(120), index=True)
    processing_status: Mapped[str] = mapped_column(String(80), default="manual", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    images: Mapped[list[ImageAsset]] = relationship(back_populates="card_instance")


class ImageAsset(Base):
    __tablename__ = "image_assets"
    __table_args__ = (
        UniqueConstraint("absolute_path", name="uq_image_assets_absolute_path"),
        Index("ix_image_assets_directory_relative", "directory_id", "relative_path"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    directory_id: Mapped[str] = mapped_column(ForeignKey("directory_roots.id"), nullable=False)
    absolute_path: Mapped[str] = mapped_column(Text, nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str] = mapped_column(String(260), nullable=False)
    extension: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    modified_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    perceptual_hash: Mapped[str | None] = mapped_column(String(32), index=True)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    exif_orientation: Mapped[int | None] = mapped_column(Integer)
    thumbnail_path: Mapped[str | None] = mapped_column(Text)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    processing_status: Mapped[str] = mapped_column(String(80), default="pending", nullable=False)
    duplicate_status: Mapped[str] = mapped_column(String(80), default="unknown", nullable=False, index=True)
    front_back_assignment: Mapped[str | None] = mapped_column(String(40), index=True)
    original_location: Mapped[str] = mapped_column(Text, nullable=False)
    card_instance_id: Mapped[str | None] = mapped_column(ForeignKey("card_instances.id"), index=True)
    error_message: Mapped[str | None] = mapped_column(Text)

    directory: Mapped[DirectoryRoot] = relationship(back_populates="images")
    card_instance: Mapped[CardInstance | None] = relationship(back_populates="images")


class FieldProvenance(Base):
    __tablename__ = "field_provenance"
    __table_args__ = (Index("ix_field_provenance_entity", "entity_type", "entity_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    field_name: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    normalized_value: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_identifier: Mapped[str | None] = mapped_column(String(200))
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    model_or_engine: Mapped[str | None] = mapped_column(String(120))
    schema_version: Mapped[str] = mapped_column(String(40), default="1", nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(40))
    user_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_status_type", "status", "type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="queued", nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    cancellation_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_action_created", "action", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    sensitive_redacted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
