"""add session expiry

Revision ID: 003
Revises: 002
Create Date: 2026-02-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавление колонки expires_at
    op.add_column(
        'survey_sessions',
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='Время автоматического истечения сессии')
    )
    
    # Установка expires_at для существующих незавершенных сессий (started_at + 2 часа)
    op.execute("""
        UPDATE survey_sessions 
        SET expires_at = started_at + INTERVAL '2 hours'
        WHERE status = 'in_progress' AND expires_at IS NULL
    """)


def downgrade() -> None:
    op.drop_column('survey_sessions', 'expires_at')
