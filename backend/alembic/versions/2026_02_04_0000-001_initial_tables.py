"""
Инициализация базы данных - создание таблиц

Revision ID: 001
Revises: 
Create Date: 2026-02-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Применение миграции - создание таблиц."""
    
    # Таблица конфигураций опросника
    op.create_table(
        'survey_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False, comment='Название опросника'),
        sa.Column('description', sa.Text(), nullable=True, comment='Описание'),
        sa.Column('json_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='JSON-структура опросника'),
        sa.Column('version', sa.String(length=50), nullable=True, comment='Версия опросника'),
        sa.Column('is_active', sa.Boolean(), nullable=True, comment='Активен ли опросник'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_survey_configs_id'), 'survey_configs', ['id'], unique=False)

    # Таблица сессий опроса
    op.create_table(
        'survey_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False, comment='ID сделки/лида в Битрикс24'),
        sa.Column('entity_type', sa.String(length=10), nullable=True, comment='Тип сущности: DEAL или LEAD'),
        sa.Column('patient_name', sa.String(length=255), nullable=True, comment='Имя пациента (для приветствия)'),
        sa.Column('survey_config_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, comment='Статус: in_progress, completed, abandoned'),
        sa.Column('consent_given', sa.Boolean(), nullable=True, comment='Дано согласие на обработку ПДн'),
        sa.Column('consent_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['survey_config_id'], ['survey_configs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_survey_sessions_created', 'survey_sessions', ['started_at'], unique=False)
    op.create_index('ix_survey_sessions_lead_status', 'survey_sessions', ['lead_id', 'status'], unique=False)
    op.create_index(op.f('ix_survey_sessions_lead_id'), 'survey_sessions', ['lead_id'], unique=False)
    op.create_index(op.f('ix_survey_sessions_token_hash'), 'survey_sessions', ['token_hash'], unique=True)

    # Таблица ответов
    op.create_table(
        'survey_answers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('node_id', sa.String(length=100), nullable=False, comment='ID вопроса из JSON-конфига'),
        sa.Column('answer_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Ответ пользователя в JSON формате'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['survey_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_survey_answers_session_node', 'survey_answers', ['session_id', 'node_id'], unique=False)
    op.create_index(op.f('ix_survey_answers_id'), 'survey_answers', ['id'], unique=False)

    # Таблица аудита
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False, comment='Тип действия'),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Детали действия'),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['survey_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)


def downgrade() -> None:
    """Откат миграции - удаление таблиц."""
    op.drop_index(op.f('ix_audit_logs_timestamp'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
    
    op.drop_index(op.f('ix_survey_answers_id'), table_name='survey_answers')
    op.drop_index('ix_survey_answers_session_node', table_name='survey_answers')
    op.drop_table('survey_answers')
    
    op.drop_index(op.f('ix_survey_sessions_token_hash'), table_name='survey_sessions')
    op.drop_index(op.f('ix_survey_sessions_lead_id'), table_name='survey_sessions')
    op.drop_index('ix_survey_sessions_lead_status', table_name='survey_sessions')
    op.drop_index('ix_survey_sessions_created', table_name='survey_sessions')
    op.drop_table('survey_sessions')
    
    op.drop_index(op.f('ix_survey_configs_id'), table_name='survey_configs')
    op.drop_table('survey_configs')
