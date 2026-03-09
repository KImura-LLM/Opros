"""
Добавление колонки report_snapshot в таблицу survey_sessions.

Колонка хранит «запечатанный» снимок отчёта (HTML + TXT), сформированного
в момент завершения опроса. Это позволяет:
- Просматривать отчёт в том виде, каким он был на момент прохождения опроса.
- Изменения в структуре групп, триггерах или логике системного анализа,
  сделанные после даты прохождения, НЕ влияют на уже сохранённые отчёты.
- Принудительное обновление отчёта возможно только через явное действие
  администратора (кнопка «Обновить отчёт»).

Revision ID: 005
Revises: 004
Create Date: 2026-03-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавление колонки report_snapshot."""
    op.add_column(
        'survey_sessions',
        sa.Column(
            'report_snapshot',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment=(
                'Снимок отчёта на момент завершения опроса. '
                'Структура: {"html": "...", "txt": "...", '
                '"generated_at": "ISO8601", "config_version": "...", "regenerated": bool}'
            ),
        ),
    )


def downgrade() -> None:
    """Удаление колонки report_snapshot."""
    op.drop_column('survey_sessions', 'report_snapshot')
