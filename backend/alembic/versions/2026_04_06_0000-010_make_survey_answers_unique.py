"""
Делает ответы опроса уникальными по паре session_id + node_id.
"""

from alembic import op
import sqlalchemy as sa


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


INDEX_NAME = "ix_survey_answers_session_node"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"]: index for index in inspector.get_indexes("survey_answers")}

    op.execute(
        sa.text(
            """
            DELETE FROM survey_answers
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY session_id, node_id
                            ORDER BY COALESCE(updated_at, created_at) DESC, id DESC
                        ) AS rn
                    FROM survey_answers
                ) ranked
                WHERE ranked.rn > 1
            )
            """
        )
    )

    existing_index = indexes.get(INDEX_NAME)
    if existing_index:
        op.drop_index(INDEX_NAME, table_name="survey_answers")

    op.create_index(
        INDEX_NAME,
        "survey_answers",
        ["session_id", "node_id"],
        unique=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"]: index for index in inspector.get_indexes("survey_answers")}

    if INDEX_NAME in indexes:
        op.drop_index(INDEX_NAME, table_name="survey_answers")

    op.create_index(
        INDEX_NAME,
        "survey_answers",
        ["session_id", "node_id"],
        unique=False,
    )
