"""
Добавляет очередь и результат ИИ-анализа анкеты.

Revision ID: 013
Revises: 012
Create Date: 2026-05-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "survey_ai_analyses" not in tables:
        op.create_table(
            "survey_ai_analyses",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False, comment="Одна актуальная ИИ-задача на анкету"),
            sa.Column("analysis_case_id", postgresql.UUID(as_uuid=True), nullable=False, comment="Случайный внешний ID без связи с пациентом/CRM"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending", comment="pending, running, succeeded, failed, skipped"),
            sa.Column("model", sa.String(length=255), nullable=False),
            sa.Column("prompt_version", sa.String(length=50), nullable=False),
            sa.Column("prompt_hash", sa.String(length=64), nullable=True),
            sa.Column("request_payload_hash", sa.String(length=64), nullable=True),
            sa.Column("response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("overall_priority", sa.String(length=10), nullable=True),
            sa.Column("error_code", sa.String(length=100), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["session_id"], ["survey_sessions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("session_id", name="uq_survey_ai_analyses_session_id"),
            sa.UniqueConstraint("analysis_case_id", name="uq_survey_ai_analyses_case_id"),
        )
        op.create_index("ix_survey_ai_analyses_status_queued_at", "survey_ai_analyses", ["status", "queued_at"], unique=False)
        op.create_index("ix_survey_ai_analyses_completed_at", "survey_ai_analyses", ["completed_at"], unique=False)
        op.create_index("ix_survey_ai_analyses_overall_priority", "survey_ai_analyses", ["overall_priority"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "survey_ai_analyses" in tables:
        op.drop_index("ix_survey_ai_analyses_overall_priority", table_name="survey_ai_analyses")
        op.drop_index("ix_survey_ai_analyses_completed_at", table_name="survey_ai_analyses")
        op.drop_index("ix_survey_ai_analyses_status_queued_at", table_name="survey_ai_analyses")
        op.drop_table("survey_ai_analyses")
