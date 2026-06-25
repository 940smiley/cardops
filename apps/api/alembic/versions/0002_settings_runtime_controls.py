"""settings runtime controls

Revision ID: 0002_settings_runtime_controls
Revises: 0001_initial
Create Date: 2026-06-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_settings_runtime_controls"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("settings", sa.Column("demo_mode", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column(
        "settings",
        sa.Column("listing_export_mode", sa.String(length=40), nullable=False, server_default="file_upload"),
    )
    op.add_column(
        "settings",
        sa.Column("ebay_direct_listing_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "settings",
        sa.Column("ebay_marketplace_id", sa.String(length=40), nullable=False, server_default="EBAY_US"),
    )
    op.add_column("settings", sa.Column("ebay_merchant_location_key", sa.String(length=120), nullable=True))
    op.add_column("settings", sa.Column("ebay_payment_policy_id", sa.String(length=120), nullable=True))
    op.add_column("settings", sa.Column("ebay_return_policy_id", sa.String(length=120), nullable=True))
    op.add_column("settings", sa.Column("ebay_fulfillment_policy_id", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("settings", "ebay_fulfillment_policy_id")
    op.drop_column("settings", "ebay_return_policy_id")
    op.drop_column("settings", "ebay_payment_policy_id")
    op.drop_column("settings", "ebay_merchant_location_key")
    op.drop_column("settings", "ebay_marketplace_id")
    op.drop_column("settings", "ebay_direct_listing_enabled")
    op.drop_column("settings", "listing_export_mode")
    op.drop_column("settings", "demo_mode")
