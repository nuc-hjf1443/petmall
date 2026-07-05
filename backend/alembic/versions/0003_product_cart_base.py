"""create product category sku and cart tables

Revision ID: 0003_product_cart_base
Revises: 0002_c_adoption_merchant_agent
Create Date: 2026-07-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_product_cart_base"
down_revision: str | None = "0002_c_adoption_merchant_agent"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_category",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["product_category.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_product_category_id"), "product_category", ["id"], unique=False)
    op.create_index(
        op.f("ix_product_category_parent_id"),
        "product_category",
        ["parent_id"],
        unique=False,
    )

    op.create_table(
        "product",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("merchant_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("cover_image", sa.String(length=512), nullable=True),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("original_price", sa.Integer(), nullable=True),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("applicable_pet_type", sa.String(length=64), nullable=True),
        sa.Column("audit_reason", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("audited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("price >= 0", name="ck_product_price_non_negative"),
        sa.CheckConstraint(
            "original_price IS NULL OR original_price >= 0",
            name="ck_product_original_price_non_negative",
        ),
        sa.CheckConstraint("stock >= 0", name="ck_product_stock_non_negative"),
        sa.CheckConstraint(
            "status IN ('draft', 'pending', 'on_sale', 'off_shelf', 'rejected')",
            name="ck_product_status_valid",
        ),
        sa.ForeignKeyConstraint(["category_id"], ["product_category.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_product_applicable_pet_type"),
        "product",
        ["applicable_pet_type"],
        unique=False,
    )
    op.create_index("ix_product_category_fk", "product", ["category_id"], unique=False)
    op.create_index(op.f("ix_product_id"), "product", ["id"], unique=False)
    op.create_index(op.f("ix_product_merchant_id"), "product", ["merchant_id"], unique=False)
    op.create_index(op.f("ix_product_status"), "product", ["status"], unique=False)
    op.create_index(op.f("ix_product_title"), "product", ["title"], unique=False)

    op.create_table(
        "product_sku",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("specs", sa.JSON(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("original_price", sa.Integer(), nullable=True),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("price >= 0", name="ck_product_sku_price_non_negative"),
        sa.CheckConstraint(
            "original_price IS NULL OR original_price >= 0",
            name="ck_product_sku_original_price_non_negative",
        ),
        sa.CheckConstraint("stock >= 0", name="ck_product_sku_stock_non_negative"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku_code"),
    )
    op.create_index(op.f("ix_product_sku_id"), "product_sku", ["id"], unique=False)
    op.create_index(
        op.f("ix_product_sku_product_id"),
        "product_sku",
        ["product_id"],
        unique=False,
    )

    op.create_table(
        "product_image",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=512), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_product_image_sort_order_non_negative",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_image_id"), "product_image", ["id"], unique=False)
    op.create_index(
        op.f("ix_product_image_product_id"),
        "product_image",
        ["product_id"],
        unique=False,
    )

    op.create_table(
        "product_review",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("order_item_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "rating BETWEEN 1 AND 5",
            name="ck_product_review_rating_valid",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.ForeignKeyConstraint(["sku_id"], ["product_sku.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_item_id", name="uq_product_review_order_item_id"),
    )
    op.create_index(op.f("ix_product_review_id"), "product_review", ["id"], unique=False)
    op.create_index(
        op.f("ix_product_review_product_id"),
        "product_review",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_review_sku_id"),
        "product_review",
        ["sku_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_review_user_id"),
        "product_review",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "cart_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "quantity BETWEEN 1 AND 99",
            name="ck_cart_item_quantity_valid",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.ForeignKeyConstraint(["sku_id"], ["product_sku.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "sku_id", name="uq_cart_item_user_id_sku_id"),
    )
    op.create_index(op.f("ix_cart_item_id"), "cart_item", ["id"], unique=False)
    op.create_index(op.f("ix_cart_item_product_id"), "cart_item", ["product_id"], unique=False)
    op.create_index(op.f("ix_cart_item_sku_id"), "cart_item", ["sku_id"], unique=False)
    op.create_index(op.f("ix_cart_item_user_id"), "cart_item", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_cart_item_user_id"), table_name="cart_item")
    op.drop_index(op.f("ix_cart_item_sku_id"), table_name="cart_item")
    op.drop_index(op.f("ix_cart_item_product_id"), table_name="cart_item")
    op.drop_index(op.f("ix_cart_item_id"), table_name="cart_item")
    op.drop_table("cart_item")

    op.drop_index(op.f("ix_product_review_user_id"), table_name="product_review")
    op.drop_index(op.f("ix_product_review_sku_id"), table_name="product_review")
    op.drop_index(op.f("ix_product_review_product_id"), table_name="product_review")
    op.drop_index(op.f("ix_product_review_id"), table_name="product_review")
    op.drop_table("product_review")

    op.drop_index(op.f("ix_product_image_product_id"), table_name="product_image")
    op.drop_index(op.f("ix_product_image_id"), table_name="product_image")
    op.drop_table("product_image")

    op.drop_index(op.f("ix_product_sku_product_id"), table_name="product_sku")
    op.drop_index(op.f("ix_product_sku_id"), table_name="product_sku")
    op.drop_table("product_sku")

    op.drop_index(op.f("ix_product_title"), table_name="product")
    op.drop_index(op.f("ix_product_status"), table_name="product")
    op.drop_index(op.f("ix_product_merchant_id"), table_name="product")
    op.drop_index(op.f("ix_product_id"), table_name="product")
    op.drop_index("ix_product_category_fk", table_name="product")
    op.drop_index(op.f("ix_product_applicable_pet_type"), table_name="product")
    op.drop_table("product")

    op.drop_index(op.f("ix_product_category_parent_id"), table_name="product_category")
    op.drop_index(op.f("ix_product_category_id"), table_name="product_category")
    op.drop_table("product_category")
