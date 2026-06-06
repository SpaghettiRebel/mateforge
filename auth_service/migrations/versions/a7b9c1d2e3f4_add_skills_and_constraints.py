"""add skills and subscription constraints

Revision ID: a7b9c1d2e3f4
Revises: 2de139d97a28
Create Date: 2026-06-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a7b9c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "2de139d97a28"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_subscriptions_not_self",
        "subscriptions",
        "subscriber_id <> author_id",
    )

    op.create_table(
        "skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("group", sa.String(length=30), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_skills_group"), "skills", ["group"], unique=False)
    op.create_index(op.f("ix_skills_name"), "skills", ["name"], unique=True)
    op.create_index(op.f("ix_skills_slug"), "skills", ["slug"], unique=True)

    op.create_table(
        "user_skills",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "skill_id"),
    )


def downgrade() -> None:
    op.drop_table("user_skills")
    op.drop_index(op.f("ix_skills_slug"), table_name="skills")
    op.drop_index(op.f("ix_skills_name"), table_name="skills")
    op.drop_index(op.f("ix_skills_group"), table_name="skills")
    op.drop_table("skills")
    op.drop_constraint("ck_subscriptions_not_self", "subscriptions", type_="check")
