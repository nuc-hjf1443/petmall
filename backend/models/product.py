from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class ProductStatus(StrEnum):
    DRAFT = "draft"
    PENDING = "pending"
    ON_SALE = "on_sale"
    OFF_SHELF = "off_shelf"
    REJECTED = "rejected"


class ProductCategory(Base, TimestampMixin):
    __tablename__ = "product_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_category.id"),
        index=True,
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parent: Mapped["ProductCategory | None"] = relationship(
        remote_side="ProductCategory.id",
        back_populates="children",
    )
    children: Mapped[list["ProductCategory"]] = relationship(back_populates="parent")
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base, TimestampMixin):
    __tablename__ = "product"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_product_price_non_negative"),
        CheckConstraint(
            "original_price IS NULL OR original_price >= 0",
            name="ck_product_original_price_non_negative",
        ),
        CheckConstraint("stock >= 0", name="ck_product_stock_non_negative"),
        CheckConstraint(
            "status IN ('draft', 'pending', 'on_sale', 'off_shelf', 'rejected')",
            name="ck_product_status_valid",
        ),
        Index("ix_product_category_fk", "category_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    merchant_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("product_category.id"),
        nullable=False,
    )
    brand: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    cover_image: Mapped[str | None] = mapped_column(String(512), nullable=True)
    price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    original_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default=ProductStatus.DRAFT.value,
        index=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    applicable_pet_type: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    audit_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    audited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    category: Mapped[ProductCategory] = relationship(back_populates="products", lazy="selectin")
    skus: Mapped[list["ProductSku"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ProductImage.sort_order, ProductImage.id",
    )
    reviews: Mapped[list["ProductReview"]] = relationship(
        back_populates="product",
        lazy="selectin",
    )


class ProductSku(Base, TimestampMixin):
    __tablename__ = "product_sku"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_product_sku_price_non_negative"),
        CheckConstraint(
            "original_price IS NULL OR original_price >= 0",
            name="ck_product_sku_original_price_non_negative",
        ),
        CheckConstraint("stock >= 0", name="ck_product_sku_stock_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True, nullable=False)
    sku_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    specs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    original_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    product: Mapped[Product] = relationship(back_populates="skus")


class ProductImage(Base, TimestampMixin):
    __tablename__ = "product_image"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="ck_product_image_sort_order_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True, nullable=False)
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    product: Mapped[Product] = relationship(back_populates="images")


class ProductReview(Base, TimestampMixin):
    __tablename__ = "product_review"
    __table_args__ = (
        UniqueConstraint("order_item_id", name="uq_product_review_order_item_id"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_product_review_rating_valid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True, nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("product_sku.id"), index=True, nullable=False)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_item.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    product: Mapped[Product] = relationship(back_populates="reviews")
    sku: Mapped[ProductSku] = relationship(lazy="selectin")


class ProductFavorite(Base, TimestampMixin):
    __tablename__ = "product_favorite"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_product_favorite_user_product"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True, nullable=False)

    product: Mapped[Product] = relationship(lazy="selectin")


class CartItem(Base, TimestampMixin):
    __tablename__ = "cart_item"
    __table_args__ = (
        UniqueConstraint("user_id", "sku_id", name="uq_cart_item_user_id_sku_id"),
        CheckConstraint(
            "quantity BETWEEN 1 AND 99",
            name="ck_cart_item_quantity_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True, nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("product_sku.id"), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    selected: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    product: Mapped[Product] = relationship(lazy="selectin")
    sku: Mapped[ProductSku] = relationship(lazy="selectin")
