"""add metric results and session capture metadata

Revision ID: 0f8b3f5f9d2a
Revises: 5e2f6bf1540f
Create Date: 2026-04-20 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0f8b3f5f9d2a"
down_revision = "5e2f6bf1540f"
branch_labels = None
depends_on = None

camera_view_enum = postgresql.ENUM(
    "FRONTAL",
    "LEFT_SAGITTAL",
    "RIGHT_SAGITTAL",
    name="camera_view_enum",
    create_type=False,
)
dominant_side_enum = postgresql.ENUM(
    "LEFT",
    "RIGHT",
    name="dominant_side_enum",
    create_type=False,
)
computation_status_enum = postgresql.ENUM(
    "COMPUTED",
    "NOT_COMPUTABLE",
    name="computation_status_enum",
    create_type=False,
)
severity_level_enum = postgresql.ENUM(
    "MINOR",
    "MODERATE",
    "SEVERE",
    name="severity_level_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    camera_view_enum.create(bind, checkfirst=True)
    dominant_side_enum.create(bind, checkfirst=True)
    computation_status_enum.create(bind, checkfirst=True)

    op.add_column(
        "training_sessions",
        sa.Column("camera_view", camera_view_enum, nullable=True),
    )
    op.add_column(
        "training_sessions",
        sa.Column("dominant_side", dominant_side_enum, nullable=True),
    )

    op.create_table(
        "metric_results",
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("metric_id", sa.UUID(), nullable=False),
        sa.Column("phase_id", sa.String(length=80), nullable=False),
        sa.Column("raw_value", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("ideal_min", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("ideal_max", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("deviation", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("severity_level", severity_level_enum, nullable=False),
        sa.Column("normalized_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("affected_body_part", sa.String(length=120), nullable=False),
        sa.Column("computation_status", computation_status_enum, nullable=False),
        sa.Column("valid_frame_count", sa.Integer(), nullable=False),
        sa.Column(
            "formula_version",
            sa.String(length=32),
            server_default=sa.text("'phase0_v0_1_0'"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["metric_id"],
            ["metric_types.id"],
            name=op.f("fk_metric_results_metric_id_metric_types"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["training_sessions.id"],
            name=op.f("fk_metric_results_session_id_training_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_metric_results")),
    )
    op.create_index(
        op.f("ix_metric_results_metric_id"),
        "metric_results",
        ["metric_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_metric_results_session_id"),
        "metric_results",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(op.f("ix_metric_results_session_id"), table_name="metric_results")
    op.drop_index(op.f("ix_metric_results_metric_id"), table_name="metric_results")
    op.drop_table("metric_results")

    op.drop_column("training_sessions", "dominant_side")
    op.drop_column("training_sessions", "camera_view")

    computation_status_enum.drop(bind, checkfirst=True)
    dominant_side_enum.drop(bind, checkfirst=True)
    camera_view_enum.drop(bind, checkfirst=True)
