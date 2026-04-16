"""add session artifacts

Revision ID: 5e2f6bf1540f
Revises: 908464950add
Create Date: 2026-04-16 17:05:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5e2f6bf1540f"
down_revision = "908464950add"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_artifacts",
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("artifact_type", sa.String(length=80), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["training_sessions.id"],
            name=op.f("fk_session_artifacts_session_id_training_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_session_artifacts")),
        sa.UniqueConstraint(
            "session_id",
            "artifact_type",
            name="uq_session_artifact_type",
        ),
    )
    op.create_index(
        op.f("ix_session_artifacts_artifact_type"),
        "session_artifacts",
        ["artifact_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_session_artifacts_session_id"),
        "session_artifacts",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_session_artifacts_session_id"), table_name="session_artifacts")
    op.drop_index(
        op.f("ix_session_artifacts_artifact_type"),
        table_name="session_artifacts",
    )
    op.drop_table("session_artifacts")
