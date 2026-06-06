"""add tags and pending invitation constraints

Revision ID: f1a2b3c4d5e6
Revises: e0b295b13e8d
Create Date: 2026-06-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e0b295b13e8d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("tags"):
        op.create_table(
            "tags",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(length=50), nullable=False),
            sa.Column("slug", sa.String(length=50), nullable=False),
            sa.Column("group", sa.String(length=30), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )

    tag_indexes = {
        item["name"]
        for item in sa.inspect(bind).get_indexes("tags")
    }
    if op.f("ix_tags_group") not in tag_indexes:
        op.create_index(op.f("ix_tags_group"), "tags", ["group"], unique=False)
    if op.f("ix_tags_slug") not in tag_indexes:
        op.create_index(op.f("ix_tags_slug"), "tags", ["slug"], unique=True)

    if not sa.inspect(bind).has_table("project_tags_association"):
        op.create_table(
            "project_tags_association",
            sa.Column("project_id", sa.Uuid(), nullable=False),
            sa.Column("tag_id", sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("project_id", "tag_id"),
        )

    invitation_indexes = {
        item["name"]
        for item in sa.inspect(bind).get_indexes("project_invitations")
    }
    if "uq_pending_project_invitation" not in invitation_indexes:
        op.create_index(
            "uq_pending_project_invitation",
            "project_invitations",
            ["project_id", "user_id"],
            unique=True,
            postgresql_where=sa.text("status = 'PENDING'"),
        )


def downgrade() -> None:
    op.drop_index("uq_pending_project_invitation", table_name="project_invitations")
    op.drop_table("project_tags_association")
    op.drop_index(op.f("ix_tags_slug"), table_name="tags")
    op.drop_index(op.f("ix_tags_group"), table_name="tags")
    op.drop_table("tags")
