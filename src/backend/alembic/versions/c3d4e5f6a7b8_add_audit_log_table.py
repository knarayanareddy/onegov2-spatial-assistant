"""add audit_log table

Revision ID: c3d4e5f6a7b8
Revises: b2f3a1c4d5e6
Create Date: 2026-06-04 20:50:00.000000

"""

from typing import Sequence, Union

import sqlmodel
from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2f3a1c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_oid", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("user_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("auth_mode", sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
        sa.Column("action", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("target", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("detail_json", sa.Text(), nullable=False),
        sa.Column("params_hash", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_user_oid", "audit_log", ["user_oid"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_action", table_name="audit_log")
    op.drop_index("ix_audit_log_user_oid", table_name="audit_log")
    op.drop_table("audit_log")
