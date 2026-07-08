from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProductCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int | None = None
    name: str
    sort_order: int


class ProductSkuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku_code: str
    name: str
    specs: dict[str, Any]
    price: int
    original_price: int | None = None
    stock: int
    is_enabled: bool = True


class ProductImageInput(BaseModel):
    image_url: str = Field(..., min_length=1, max_length=512)
    sort_order: int = Field(default=0, ge=0)
    is_primary: bool = False


class ProductImageResponse(ProductImageInput):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ProductSkuUpsert(BaseModel):
    id: int | None = Field(default=None, gt=0)
    sku_code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    specs: dict[str, Any] = Field(default_factory=dict)
    price: int = Field(..., ge=0)
    original_price: int | None = Field(default=None, ge=0)
    stock: int = Field(default=0, ge=0)
    is_enabled: bool = True


class ProductCreate(BaseModel):
    category_id: int = Field(..., gt=0)
    brand: str | None = Field(default=None, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    applicable_pet_type: str | None = Field(default=None, max_length=64)
    skus: list[ProductSkuUpsert] = Field(..., min_length=1)
    images: list[ProductImageInput] = Field(..., min_length=1, max_length=10)


class ProductUpdate(BaseModel):
    category_id: int | None = Field(default=None, gt=0)
    brand: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    applicable_pet_type: str | None = Field(default=None, max_length=64)
    skus: list[ProductSkuUpsert] | None = Field(default=None, min_length=1)
    images: list[ProductImageInput] | None = Field(
        default=None,
        min_length=1,
        max_length=10,
    )


class ProductSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant_id: int
    category_id: int
    brand: str | None = None
    title: str
    cover_image: str | None = None
    price: int
    original_price: int | None = None
    stock: int
    applicable_pet_type: str | None = None


class ProductDetailResponse(ProductSummaryResponse):
    status: str
    description: str | None = None
    skus: list[ProductSkuResponse]
    images: list[ProductImageResponse]
    audit_reason: str | None = None
    submitted_at: datetime | None = None
    audited_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    items: list[ProductSummaryResponse]
    total: int
    page: int
    page_size: int


class ProductReviewCreate(BaseModel):
    order_item_id: int = Field(..., gt=0)
    rating: int = Field(..., ge=1, le=5)
    content: str | None = Field(default=None, max_length=2000)
    is_anonymous: bool = False


class ProductReviewResponse(BaseModel):
    id: int
    user_id: int | None
    product_id: int
    sku_id: int
    sku_name: str
    rating: int
    content: str | None = None
    is_anonymous: bool
    created_at: datetime


class ProductReviewListResponse(BaseModel):
    items: list[ProductReviewResponse]
    total: int
    average_rating: float | None
    page: int
    page_size: int
