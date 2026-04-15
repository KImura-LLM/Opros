"""
Добавляет настройки видимости данных для учетных записей врачей.

Revision ID: 011
Revises: 010
Create Date: 2026-04-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "doctor_users" not in inspector.get_table_names():
        return

    doctor_columns = {column["name"] for column in inspector.get_columns("doctor_users")}

    if "allowed_clinic_bucket" not in doctor_columns:
        op.add_column(
            "doctor_users",
            sa.Column(
                "allowed_clinic_bucket",
                sa.String(length=50),
                nullable=True,
                comment="Разрешенная воронка doctor portal: novosibirsk, kemerovo, yaroslavl",
            ),
        )

    if "session_doctor_name_filter" not in doctor_columns:
        op.add_column(
            "doctor_users",
            sa.Column(
                "session_doctor_name_filter",
                sa.String(length=255),
                nullable=True,
                comment="Жесткий фильтр doctor portal по точному ФИО врача",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "doctor_users" not in inspector.get_table_names():
        return

    doctor_columns = {column["name"] for column in inspector.get_columns("doctor_users")}

    if "session_doctor_name_filter" in doctor_columns:
        op.drop_column("doctor_users", "session_doctor_name_filter")

    if "allowed_clinic_bucket" in doctor_columns:
        op.drop_column("doctor_users", "allowed_clinic_bucket")
