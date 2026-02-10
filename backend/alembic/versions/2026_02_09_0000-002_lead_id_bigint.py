"""
Изменение типа lead_id с INTEGER на BIGINT

ID сделок Битрикс24 могут превышать максимальное значение int32 (2 147 483 647).
Переводим lead_id на BIGINT для поддержки больших значений.

Revision ID: 002
Revises: 001
Create Date: 2026-02-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Изменение lead_id с INTEGER на BIGINT."""
    op.alter_column(
        'survey_sessions',
        'lead_id',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        existing_comment='ID сделки/лида в Битрикс24',
    )


def downgrade() -> None:
    """Откат: lead_id обратно в INTEGER."""
    op.alter_column(
        'survey_sessions',
        'lead_id',
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
        existing_comment='ID сделки/лида в Битрикс24',
    )
