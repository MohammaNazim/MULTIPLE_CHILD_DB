"""drop_query_request_logs

Revision ID: 4bccae5ae442
Revises: 6f2849364f3d
Create Date: 2026-01-07 14:10:19.112733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4bccae5ae442'
down_revision: Union[str, Sequence[str], None] = '6f2849364f3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.drop_table("query_request_logs")


def downgrade():
    op.create_table(
        "query_request_logs",
        op.Column("id", op.sa.UUID(), primary_key=True),
        op.Column("idempotency_key", op.sa.String(128), unique=True, nullable=False),
        op.Column("child_id", op.sa.UUID(), nullable=True),
        op.Column("status", op.sa.String(20)),
        op.Column("created_at", op.sa.DateTime(timezone=True)),
    )

