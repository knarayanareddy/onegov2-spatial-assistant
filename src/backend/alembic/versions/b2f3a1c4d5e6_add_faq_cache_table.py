"""add faq_cache table

Revision ID: b2f3a1c4d5e6
Revises: 7e2e6216e30f
Create Date: 2026-06-04 18:55:00.000000

"""

from typing import Sequence, Union

import sqlmodel
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2f3a1c4d5e6"
down_revision: Union[str, Sequence[str], None] = "7e2e6216e30f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "faq_cache",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cache_key", sqlmodel.sql.sqltypes.AutoString(length=512), nullable=False),
        sa.Column("question_norm", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=False),
        sa.Column("question_display", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=False),
        sa.Column("answer_nl", sa.Text(), nullable=False),
        sa.Column("sources_json", sa.Text(), nullable=False),
        sa.Column("intent", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
        sa.Column("version_stamp", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_faq_cache_cache_key", "faq_cache", ["cache_key"])
    op.create_index("ix_faq_cache_status", "faq_cache", ["status"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_faq_cache_status", table_name="faq_cache")
    op.drop_index("ix_faq_cache_cache_key", table_name="faq_cache")
    op.drop_table("faq_cache")
