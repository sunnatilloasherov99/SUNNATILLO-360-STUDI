"""Create the initial SUNNATILLO 360 STUDIO schema.

The migration also adopts databases created by the early create_all prototype.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def _tables():
    return set(inspect(op.get_bind()).get_table_names())


def _columns(table_name):
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name):
    return {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    tables = _tables()

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("email", sa.String(length=254), nullable=False),
            sa.Column("password_hash", sa.String(length=256), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "projects" not in tables:
        op.create_table(
            "projects",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("owner_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("mode", sa.String(length=16), nullable=False, server_default="manual"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("edit_settings_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("tour_json", sa.Text(), nullable=False, server_default="{}"),
        )
    else:
        existing = _columns("projects")
        missing = []
        if "owner_id" not in existing:
            missing.append(sa.Column("owner_id", sa.String(length=36), nullable=True))
        if "edit_settings_json" not in existing:
            missing.append(sa.Column("edit_settings_json", sa.Text(), nullable=False, server_default="{}"))
        if "tour_json" not in existing:
            missing.append(sa.Column("tour_json", sa.Text(), nullable=False, server_default="{}"))
        if missing:
            with op.batch_alter_table("projects") as batch:
                for column in missing:
                    batch.add_column(column)
                if "owner_id" not in existing:
                    batch.create_foreign_key("fk_projects_owner_id_users", "users", ["owner_id"], ["id"])

    if "media_assets" not in tables:
        op.create_table(
            "media_assets",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("original_name", sa.String(length=255), nullable=False),
            sa.Column("stored_name", sa.String(length=80), nullable=False, unique=True),
            sa.Column("content_type", sa.String(length=100), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    for table_name, index_name, columns, unique in (
        ("users", "ix_users_email", ["email"], True),
        ("projects", "ix_projects_owner_id", ["owner_id"], False),
        ("media_assets", "ix_media_assets_project_id", ["project_id"], False),
    ):
        if index_name not in _indexes(table_name):
            op.create_index(index_name, table_name, columns, unique=unique)


def downgrade() -> None:
    op.drop_table("media_assets")
    op.drop_table("projects")
    op.drop_table("users")
