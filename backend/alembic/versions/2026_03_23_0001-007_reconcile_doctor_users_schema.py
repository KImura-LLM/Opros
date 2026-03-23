"""
Доводит таблицу doctor_users до полной схемы после частично созданной структуры.

Revision ID: 007
Revises: 006
Create Date: 2026-03-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "doctor_users" not in inspector.get_table_names():
        return

    doctor_columns = {column["name"] for column in inspector.get_columns("doctor_users")}

    if "is_active" not in doctor_columns:
        op.add_column(
            "doctor_users",
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
                comment="Аккаунт активен",
            ),
        )

    if "updated_at" not in doctor_columns:
        op.add_column(
            "doctor_users",
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "doctor_users" not in inspector.get_table_names():
        return

    doctor_columns = {column["name"] for column in inspector.get_columns("doctor_users")}

    if "updated_at" in doctor_columns:
        op.drop_column("doctor_users", "updated_at")

    if "is_active" in doctor_columns:
        op.drop_column("doctor_users", "is_active")
