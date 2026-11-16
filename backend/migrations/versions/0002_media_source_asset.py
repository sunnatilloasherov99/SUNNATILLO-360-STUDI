"""Track source media for edited derivatives."""

from alembic import op
import sqlalchemy as sa

revision = "0002_media_source_asset"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("media_assets") as batch_op:
        batch_op.add_column(sa.Column("source_asset_id", sa.String(length=36), nullable=True))
        batch_op.create_index("ix_media_assets_source_asset_id", ["source_asset_id"])
        batch_op.create_foreign_key(
            "fk_media_assets_source_asset_id_media_assets",
            "media_assets",
            ["source_asset_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("media_assets") as batch_op:
        batch_op.drop_constraint("fk_media_assets_source_asset_id_media_assets", type_="foreignkey")
        batch_op.drop_index("ix_media_assets_source_asset_id")
        batch_op.drop_column("source_asset_id")
