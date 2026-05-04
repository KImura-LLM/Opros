"""
Добавляет маршрутизацию опросников по клиникам и кэш CRM-полей Bitrix24.

Revision ID: 012
Revises: 011
Create Date: 2026-05-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "survey_routing_clinic_settings" not in tables:
        op.create_table(
            "survey_routing_clinic_settings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("clinic_key", sa.String(length=100), nullable=False, comment="Ключ клиники из backend-конфигурации"),
            sa.Column("default_survey_config_id", sa.Integer(), nullable=True, comment="Опросник по умолчанию для клиники"),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Маршрутизация включена"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["default_survey_config_id"], ["survey_configs.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("clinic_key"),
        )
        op.create_index(op.f("ix_survey_routing_clinic_settings_id"), "survey_routing_clinic_settings", ["id"], unique=False)
        op.create_index(op.f("ix_survey_routing_clinic_settings_clinic_key"), "survey_routing_clinic_settings", ["clinic_key"], unique=False)

    if "survey_routing_rules" not in tables:
        op.create_table(
            "survey_routing_rules",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("clinic_key", sa.String(length=100), nullable=False, comment="Ключ клиники"),
            sa.Column("name", sa.String(length=255), nullable=False, comment="Название правила"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Правило активно"),
            sa.Column("survey_config_id", sa.Integer(), nullable=False, comment="Выбранный опросник"),
            sa.Column("condition_logic", sa.String(length=10), nullable=False, server_default="AND", comment="Логика условий: AND или OR"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100", comment="Чем больше значение, тем выше приоритет"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["survey_config_id"], ["survey_configs.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_survey_routing_rules_id"), "survey_routing_rules", ["id"], unique=False)
        op.create_index(op.f("ix_survey_routing_rules_clinic_key"), "survey_routing_rules", ["clinic_key"], unique=False)
        op.create_index(
            "ix_survey_routing_rules_clinic_active_priority",
            "survey_routing_rules",
            ["clinic_key", "is_active", "priority"],
            unique=False,
        )

    if "survey_routing_conditions" not in tables:
        op.create_table(
            "survey_routing_conditions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("rule_id", sa.Integer(), nullable=False),
            sa.Column("crm_field_id", sa.String(length=255), nullable=False, comment="ID поля сделки Bitrix24"),
            sa.Column("operator", sa.String(length=50), nullable=False, comment="Оператор сравнения"),
            sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Значение условия"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["rule_id"], ["survey_routing_rules.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_survey_routing_conditions_id"), "survey_routing_conditions", ["id"], unique=False)
        op.create_index("ix_survey_routing_conditions_rule_id", "survey_routing_conditions", ["rule_id"], unique=False)

    if "bitrix_crm_fields" not in tables:
        op.create_table(
            "bitrix_crm_fields",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("entity_type", sa.String(length=20), nullable=False, server_default="DEAL", comment="Тип CRM-сущности"),
            sa.Column("field_id", sa.String(length=255), nullable=False, comment="ID поля Bitrix24"),
            sa.Column("title", sa.String(length=255), nullable=False, comment="Название поля"),
            sa.Column("type", sa.String(length=100), nullable=True, comment="Тип поля Bitrix24"),
            sa.Column("is_list", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="Поле содержит список вариантов"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Поле актуально в последней синхронизации"),
            sa.Column("raw_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Исходные metadata Bitrix24"),
            sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("entity_type", "field_id", name="uq_bitrix_crm_fields_entity_field"),
        )
        op.create_index(op.f("ix_bitrix_crm_fields_id"), "bitrix_crm_fields", ["id"], unique=False)
        op.create_index(
            "ix_bitrix_crm_fields_entity_active_title",
            "bitrix_crm_fields",
            ["entity_type", "is_active", "title"],
            unique=False,
        )

    if "bitrix_crm_field_options" not in tables:
        op.create_table(
            "bitrix_crm_field_options",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("entity_type", sa.String(length=20), nullable=False, server_default="DEAL", comment="Тип CRM-сущности"),
            sa.Column("field_id", sa.String(length=255), nullable=False, comment="ID поля Bitrix24"),
            sa.Column("option_id", sa.String(length=255), nullable=False, comment="ID варианта Bitrix24"),
            sa.Column("label", sa.String(length=255), nullable=False, comment="Отображаемый текст варианта"),
            sa.Column("sort", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("raw_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("entity_type", "field_id", "option_id", name="uq_bitrix_crm_field_options_entity_field_option"),
        )
        op.create_index(op.f("ix_bitrix_crm_field_options_id"), "bitrix_crm_field_options", ["id"], unique=False)
        op.create_index(
            "ix_bitrix_crm_field_options_field_active_label",
            "bitrix_crm_field_options",
            ["entity_type", "field_id", "is_active", "label"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "bitrix_crm_field_options" in tables:
        op.drop_index("ix_bitrix_crm_field_options_field_active_label", table_name="bitrix_crm_field_options")
        op.drop_index(op.f("ix_bitrix_crm_field_options_id"), table_name="bitrix_crm_field_options")
        op.drop_table("bitrix_crm_field_options")

    if "bitrix_crm_fields" in tables:
        op.drop_index("ix_bitrix_crm_fields_entity_active_title", table_name="bitrix_crm_fields")
        op.drop_index(op.f("ix_bitrix_crm_fields_id"), table_name="bitrix_crm_fields")
        op.drop_table("bitrix_crm_fields")

    if "survey_routing_conditions" in tables:
        op.drop_index("ix_survey_routing_conditions_rule_id", table_name="survey_routing_conditions")
        op.drop_index(op.f("ix_survey_routing_conditions_id"), table_name="survey_routing_conditions")
        op.drop_table("survey_routing_conditions")

    if "survey_routing_rules" in tables:
        op.drop_index("ix_survey_routing_rules_clinic_active_priority", table_name="survey_routing_rules")
        op.drop_index(op.f("ix_survey_routing_rules_clinic_key"), table_name="survey_routing_rules")
        op.drop_index(op.f("ix_survey_routing_rules_id"), table_name="survey_routing_rules")
        op.drop_table("survey_routing_rules")

    if "survey_routing_clinic_settings" in tables:
        op.drop_index(op.f("ix_survey_routing_clinic_settings_clinic_key"), table_name="survey_routing_clinic_settings")
        op.drop_index(op.f("ix_survey_routing_clinic_settings_id"), table_name="survey_routing_clinic_settings")
        op.drop_table("survey_routing_clinic_settings")
