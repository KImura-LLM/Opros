"""
База для портала врачей: таблица учетных записей и имя врача в сессии.

Revision ID: 006
Revises: 005
Create Date: 2026-03-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    table_names = inspector.get_table_names()
    if "doctor_users" not in table_names:
        op.create_table(
            "doctor_users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=100), nullable=False, comment="Логин врача"),
            sa.Column("hashed_password", sa.String(length=255), nullable=False, comment="Хэш пароля врача"),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
                comment="Аккаунт активен",
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    doctor_columns = {column["name"] for column in inspector.get_columns("doctor_users")}
    if "username" not in doctor_columns:
        op.add_column(
            "doctor_users",
            sa.Column("username", sa.String(length=100), nullable=False, comment="Логин врача"),
        )
    if "hashed_password" not in doctor_columns:
        op.add_column(
            "doctor_users",
            sa.Column("hashed_password", sa.String(length=255), nullable=False, comment="Хэш пароля врача"),
        )
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
    if "created_at" not in doctor_columns:
        op.add_column(
            "doctor_users",
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )
    if "updated_at" not in doctor_columns:
        op.add_column(
            "doctor_users",
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    doctor_indexes = {index["name"] for index in inspector.get_indexes("doctor_users")}
    if op.f("ix_doctor_users_id") not in doctor_indexes:
        op.create_index(op.f("ix_doctor_users_id"), "doctor_users", ["id"], unique=False)
    if op.f("ix_doctor_users_username") not in doctor_indexes:
        op.create_index(op.f("ix_doctor_users_username"), "doctor_users", ["username"], unique=True)

    session_columns = {column["name"] for column in inspector.get_columns("survey_sessions")}
    if "doctor_name" not in session_columns:
        op.add_column(
            "survey_sessions",
            sa.Column("doctor_name", sa.String(length=255), nullable=True, comment="ФИО врача из Битрикс24"),
        )


def downgrade() -> None:
    op.drop_column("survey_sessions", "doctor_name")
    op.drop_index(op.f("ix_doctor_users_username"), table_name="doctor_users")
    op.drop_index(op.f("ix_doctor_users_id"), table_name="doctor_users")
    op.drop_table("doctor_users")
