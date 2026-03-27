"""
Добавляет маршрутизацию doctor portal по воронкам Bitrix24 и право на тестовую вкладку.

Revision ID: 008
Revises: 007
Create Date: 2026-03-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    doctor_columns = {column["name"] for column in inspector.get_columns("doctor_users")}
    if "can_view_test_tab" not in doctor_columns:
        op.add_column(
            "doctor_users",
            sa.Column(
                "can_view_test_tab",
                sa.Boolean(),
                nullable=True,
                server_default=sa.text("false"),
                comment="Доступ к тестовой вкладке портала врачей",
            ),
        )
        op.execute("UPDATE doctor_users SET can_view_test_tab = false WHERE can_view_test_tab IS NULL")
        op.alter_column("doctor_users", "can_view_test_tab", nullable=False, server_default=sa.text("false"))

    session_columns = {column["name"] for column in inspector.get_columns("survey_sessions")}
    if "bitrix_category_id" not in session_columns:
        op.add_column(
            "survey_sessions",
            sa.Column("bitrix_category_id", sa.Integer(), nullable=True, comment="ID воронки в Bitrix24"),
        )

    if "portal_clinic_bucket" not in session_columns:
        op.add_column(
            "survey_sessions",
            sa.Column(
                "portal_clinic_bucket",
                sa.String(length=50),
                nullable=True,
                server_default="test",
                comment="Вкладка портала врачей: novosibirsk, kemerovo, yaroslavl, test",
            ),
        )
        op.execute("UPDATE survey_sessions SET portal_clinic_bucket = 'test' WHERE portal_clinic_bucket IS NULL")
        op.alter_column(
            "survey_sessions",
            "portal_clinic_bucket",
            nullable=False,
            server_default="test",
        )

    session_indexes = {index["name"] for index in inspector.get_indexes("survey_sessions")}
    index_name = "ix_survey_sessions_portal_bucket_status_completed"
    if index_name not in session_indexes:
        op.create_index(
            index_name,
            "survey_sessions",
            ["portal_clinic_bucket", "status", "completed_at"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_survey_sessions_portal_bucket_status_completed", table_name="survey_sessions")
    op.drop_column("survey_sessions", "portal_clinic_bucket")
    op.drop_column("survey_sessions", "bitrix_category_id")
    op.drop_column("doctor_users", "can_view_test_tab")
