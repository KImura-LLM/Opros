"""
Добавляет сохранение даты и времени приема для doctor portal.
"""

from alembic import op
import sqlalchemy as sa


revision = "2026_03_31_0000-009"
down_revision = "2026_03_27_0000-008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    session_columns = {column["name"] for column in inspector.get_columns("survey_sessions")}

    if "appointment_at" not in session_columns:
        op.add_column(
            "survey_sessions",
            sa.Column(
                "appointment_at",
                sa.String(length=50),
                nullable=True,
                comment="Дата и время приема из Bitrix24",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    session_columns = {column["name"] for column in inspector.get_columns("survey_sessions")}

    if "appointment_at" in session_columns:
        op.drop_column("survey_sessions", "appointment_at")
