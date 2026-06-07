"""harden user skills association

Revision ID: b8c0d2e4f6a8
Revises: a7b9c1d2e3f4
Create Date: 2026-06-07 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8c0d2e4f6a8"
down_revision: Union[str, Sequence[str], None] = "a7b9c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    checks = {
        item["name"]
        for item in inspector.get_check_constraints("user_skills")
    }
    if "ck_user_skills_level" not in checks:
        op.create_check_constraint(
            "ck_user_skills_level",
            "user_skills",
            "level BETWEEN 1 AND 4",
        )

    indexes = {
        item["name"]
        for item in sa.inspect(bind).get_indexes("user_skills")
    }
    if "ix_user_skills_skill_id" not in indexes:
        op.create_index(
            "ix_user_skills_skill_id",
            "user_skills",
            ["skill_id"],
            unique=False,
        )

    op.alter_column(
        "user_skills",
        "level",
        existing_type=sa.Integer(),
        nullable=False,
        server_default=sa.text("1"),
    )


def downgrade() -> None:
    op.alter_column(
        "user_skills",
        "level",
        existing_type=sa.Integer(),
        nullable=False,
        server_default=None,
    )
    op.drop_index("ix_user_skills_skill_id", table_name="user_skills")
    op.drop_constraint("ck_user_skills_level", "user_skills", type_="check")
