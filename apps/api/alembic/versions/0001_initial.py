"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("local_only_mode", sa.Boolean(), nullable=False),
        sa.Column("cloud_ai_enabled", sa.Boolean(), nullable=False),
        sa.Column("live_ebay_publishing_enabled", sa.Boolean(), nullable=False),
        sa.Column("physical_file_moves_enabled", sa.Boolean(), nullable=False),
        sa.Column("daily_ai_request_limit", sa.Integer(), nullable=False),
        sa.Column("daily_ai_cost_limit", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "card_instances",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("internal_sku", sa.String(length=50), nullable=False),
        sa.Column("sport", sa.String(length=80), nullable=True),
        sa.Column("player", sa.String(length=200), nullable=True),
        sa.Column("team", sa.String(length=160), nullable=True),
        sa.Column("manufacturer", sa.String(length=160), nullable=True),
        sa.Column("brand", sa.String(length=160), nullable=True),
        sa.Column("set_name", sa.String(length=240), nullable=True),
        sa.Column("set_year", sa.Integer(), nullable=True),
        sa.Column("card_number", sa.String(length=80), nullable=True),
        sa.Column("subset", sa.String(length=160), nullable=True),
        sa.Column("variation", sa.String(length=160), nullable=True),
        sa.Column("parallel", sa.String(length=160), nullable=True),
        sa.Column("rookie", sa.Boolean(), nullable=False),
        sa.Column("autograph", sa.Boolean(), nullable=False),
        sa.Column("relic", sa.Boolean(), nullable=False),
        sa.Column("serial_number_current", sa.Integer(), nullable=True),
        sa.Column("serial_number_total", sa.Integer(), nullable=True),
        sa.Column("raw_or_graded", sa.String(length=40), nullable=False),
        sa.Column("grading_company", sa.String(length=80), nullable=True),
        sa.Column("grade", sa.String(length=40), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("condition_notes", sa.Text(), nullable=True),
        sa.Column("acquisition_cost", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("estimated_value", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("verified_sale_low", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("verified_sale_high", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("storage_location", sa.String(length=160), nullable=True),
        sa.Column("current_lot_assignment", sa.String(length=120), nullable=True),
        sa.Column("current_ebay_listing", sa.String(length=120), nullable=True),
        sa.Column("processing_status", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("internal_sku"),
    )
    op.create_table(
        "directory_roots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=True),
        sa.Column("recursive", sa.Boolean(), nullable=False),
        sa.Column("exclude_patterns", sa.JSON(), nullable=False),
        sa.Column("allow_symlinks", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("path"),
    )
    op.create_table(
        "field_provenance",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("field_name", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_identifier", sa.String(length=200), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_or_engine", sa.String(length=120), nullable=True),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("prompt_version", sa.String(length=40), nullable=True),
        sa.Column("user_override", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("cancellation_requested", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("sensitive_redacted", sa.Boolean(), nullable=False),
        sa.Column("correlation_id", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "image_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("directory_id", sa.String(length=36), nullable=False),
        sa.Column("absolute_path", sa.Text(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(length=260), nullable=False),
        sa.Column("extension", sa.String(length=20), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("created_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modified_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("perceptual_hash", sa.String(length=32), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("exif_orientation", sa.Integer(), nullable=True),
        sa.Column("thumbnail_path", sa.Text(), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processing_status", sa.String(length=80), nullable=False),
        sa.Column("duplicate_status", sa.String(length=80), nullable=False),
        sa.Column("front_back_assignment", sa.String(length=40), nullable=True),
        sa.Column("original_location", sa.Text(), nullable=False),
        sa.Column("card_instance_id", sa.String(length=36), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["card_instance_id"], ["card_instances.id"]),
        sa.ForeignKeyConstraint(["directory_id"], ["directory_roots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("absolute_path", name="uq_image_assets_absolute_path"),
    )
    for table, columns in {
        "card_instances": [
            "internal_sku",
            "sport",
            "player",
            "team",
            "manufacturer",
            "set_name",
            "set_year",
            "card_number",
            "storage_location",
            "current_lot_assignment",
            "current_ebay_listing",
        ],
        "image_assets": [
            "extension",
            "modified_time",
            "sha256",
            "perceptual_hash",
            "duplicate_status",
            "front_back_assignment",
            "card_instance_id",
        ],
        "jobs": ["status"],
    }.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])
    op.create_index("ix_image_assets_directory_relative", "image_assets", ["directory_id", "relative_path"])
    op.create_index("ix_field_provenance_entity", "field_provenance", ["entity_type", "entity_id"])
    op.create_index("ix_jobs_status_type", "jobs", ["status", "type"])
    op.create_index("ix_audit_logs_action_created", "audit_logs", ["action", "created_at"])


def downgrade() -> None:
    op.drop_table("image_assets")
    op.drop_table("audit_logs")
    op.drop_table("jobs")
    op.drop_table("field_provenance")
    op.drop_table("directory_roots")
    op.drop_table("card_instances")
    op.drop_table("settings")
