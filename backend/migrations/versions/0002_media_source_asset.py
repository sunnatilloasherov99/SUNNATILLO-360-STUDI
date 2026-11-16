"""Track source media for edited derivatives."""

from alembic import op
import sqlalchemy as sa

revision = "0002_media_source_asset"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("media_assets", sa.Column("source_asset_id", sa.String(length=36), nullable=True))
    op.create_index("ix_media_assets_source_asset_id", "media_assets", ["source_asset_id"])
    op.create_foreign_key(
        "fk_media_assets_source_asset_id_media_assets",
        "media_assets",
        "media_assets",
        ["source_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_media_assets_source_asset_id_media_assets", "media_assets", type_="foreignkey")
    op.drop_index("ix_media_assets_source_asset_id", table_name="media_assets")
    op.drop_column("media_assets", "source_asset_id")
