"""deeper settings controls

Revision ID: 0003_deeper_settings_controls
Revises: 0002_settings_runtime_controls
Create Date: 2026-06-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_deeper_settings_controls"
down_revision = "0002_settings_runtime_controls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("settings", sa.Column("ebay_sync_limit", sa.Integer(), nullable=False, server_default="25"))
    op.add_column("settings", sa.Column("ebay_sync_offset", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "settings",
        sa.Column("ebay_sync_include_offers", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "settings",
        sa.Column("default_listing_format", sa.String(length=40), nullable=False, server_default="fixed_price"),
    )
    op.add_column("settings", sa.Column("confidence_threshold", sa.Float(), nullable=False, server_default="0.72"))
    op.add_column("settings", sa.Column("tesseract_cmd", sa.Text(), nullable=True))
    op.add_column("settings", sa.Column("ocr_language", sa.String(length=40), nullable=False, server_default="eng"))
    op.add_column("settings", sa.Column("default_input_dir", sa.Text(), nullable=True))
    op.add_column("settings", sa.Column("default_output_dir", sa.Text(), nullable=True))
    op.add_column("settings", sa.Column("default_inventory_path", sa.Text(), nullable=True))
    op.add_column("settings", sa.Column("default_ebay_export_path", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("settings", "default_ebay_export_path")
    op.drop_column("settings", "default_inventory_path")
    op.drop_column("settings", "default_output_dir")
    op.drop_column("settings", "default_input_dir")
    op.drop_column("settings", "ocr_language")
    op.drop_column("settings", "tesseract_cmd")
    op.drop_column("settings", "confidence_threshold")
    op.drop_column("settings", "default_listing_format")
    op.drop_column("settings", "ebay_sync_include_offers")
    op.drop_column("settings", "ebay_sync_offset")
    op.drop_column("settings", "ebay_sync_limit")
