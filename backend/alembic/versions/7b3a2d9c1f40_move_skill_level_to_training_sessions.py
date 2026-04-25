"""move skill level to training sessions

Revision ID: 7b3a2d9c1f40
Revises: 0f8b3f5f9d2a
Create Date: 2026-04-21 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "7b3a2d9c1f40"
down_revision = "0f8b3f5f9d2a"
branch_labels = None
depends_on = None

skill_level_enum = postgresql.ENUM(
    "BEGINNER",
    "INTERMEDIATE",
    "ADVANCED",
    name="skill_level_enum",
    create_type=False,
)


def upgrade() -> None:
    op.add_column(
        "training_sessions",
        sa.Column("skill_level", skill_level_enum, nullable=True),
    )
    op.execute(
        """
        UPDATE training_sessions
        SET skill_level = drills.difficulty_level
        FROM drills
        WHERE training_sessions.drill_id = drills.id
        """
    )
    op.alter_column("training_sessions", "skill_level", nullable=False)
    op.drop_column("drills", "difficulty_level")


def downgrade() -> None:
    op.add_column(
        "drills",
        sa.Column("difficulty_level", skill_level_enum, nullable=True),
    )
    op.execute("UPDATE drills SET difficulty_level = 'BEGINNER'")
    op.alter_column("drills", "difficulty_level", nullable=False)
    op.drop_column("training_sessions", "skill_level")
