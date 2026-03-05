"""
Добавление колонки duration_seconds в таблицу survey_answers
для отслеживания времени ответа на каждый вопрос.

Revision ID: 004
Revises: 003
Create Date: 2026-03-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавление колонки duration_seconds."""
    op.add_column(
        'survey_answers',
        sa.Column(
            'duration_seconds',
            sa.Integer(),
            nullable=True,
            comment='Время ответа на вопрос в секундах',
        ),
    )


def downgrade() -> None:
    """Удаление колонки duration_seconds."""
    op.drop_column('survey_answers', 'duration_seconds')
