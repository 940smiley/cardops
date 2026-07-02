"""root management and file operation manifests

Revision ID: 0004_root_management_and_file_manifests
Revises: 0003_deeper_settings_controls
Create Date: 2026-06-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_root_management_and_file_manifests"
down_revision = "0003_deeper_settings_controls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("directory_roots", sa.Column("normalized_path_key", sa.String(length=1024), nullable=True))
    op.create_index("ix_directory_roots_normalized_path_key", "directory_roots", ["normalized_path_key"])
    op.create_table(
        "file_operation_manifests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("operation_type", sa.String(length=80), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("source_root_id", sa.String(length=36), nullable=True),
        sa.Column("confirmation_required", sa.Boolean(), nullable=False),
        sa.Column("collision_policy", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("entries", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["source_root_id"], ["directory_roots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_file_operation_manifests_type_status",
        "file_operation_manifests",
        ["operation_type", "status"],
    )
    op.create_index(
        "ix_file_operation_manifests_source_root_id",
        "file_operation_manifests",
        ["source_root_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_file_operation_manifests_source_root_id", table_name="file_operation_manifests")
    op.drop_index("ix_file_operation_manifests_type_status", table_name="file_operation_manifests")
    op.drop_table("file_operation_manifests")
    op.drop_index("ix_directory_roots_normalized_path_key", table_name="directory_roots")
    op.drop_column("directory_roots", "normalized_path_key")
