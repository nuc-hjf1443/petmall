from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import bad_request, conflict, not_found
from models.product import ProductReview
from repository.product_repository import (
    get_product_by_id,
    get_product_review_by_order_item,
    get_public_product_by_id,
    get_sku_with_product,
    list_product_reviews,
)
from schemas.product_schema import (
    ProductReviewCreate,
    ProductReviewListResponse,
    ProductReviewResponse,
)


@dataclass(frozen=True)
class ReviewPurchase:
    order_item_id: int
    product_id: int
    sku_id: int


class ReviewPurchaseVerifier(Protocol):
    async def verify(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        order_item_id: int,
    ) -> ReviewPurchase: ...


class OrderReviewPurchaseVerifier:
    async def verify(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        order_item_id: int,
    ) -> ReviewPurchase:
        from services.order_service import verify_completed_purchase

        return await verify_completed_purchase(
            db, user_id=user_id, order_item_id=order_item_id
        )


def get_review_purchase_verifier() -> ReviewPurchaseVerifier:
    return OrderReviewPurchaseVerifier()


def _serialize_review(review: ProductReview) -> ProductReviewResponse:
    return ProductReviewResponse(
        id=review.id,
        user_id=None if review.is_anonymous else review.user_id,
        product_id=review.product_id,
        sku_id=review.sku_id,
        sku_name=review.sku.name,
        rating=review.rating,
        content=review.content,
        is_anonymous=review.is_anonymous,
        created_at=review.created_at,
    )


async def get_product_reviews(
    db: AsyncSession,
    product_id: int,
    *,
    page: int,
    page_size: int,
) -> ProductReviewListResponse:
    product = await get_public_product_by_id(db, product_id)
    if product is None:
        raise not_found("Product not found")
    reviews, total, average = await list_product_reviews(
        db,
        product_id,
        page=page,
        page_size=page_size,
    )
    return ProductReviewListResponse(
        items=[_serialize_review(review) for review in reviews],
        total=total,
        average_rating=round(average, 2) if average is not None else None,
        page=page,
        page_size=page_size,
    )


async def create_product_review(
    db: AsyncSession,
    user_id: int,
    product_id: int,
    payload: ProductReviewCreate,
    verifier: ReviewPurchaseVerifier,
) -> ProductReviewResponse:
    product = await get_product_by_id(db, product_id)
    if product is None:
        raise not_found("Product not found")
    existing = await get_product_review_by_order_item(db, payload.order_item_id)
    if existing is not None:
        raise conflict("Order item already reviewed")

    purchase = await verifier.verify(
        db,
        user_id=user_id,
        order_item_id=payload.order_item_id,
    )
    if purchase.order_item_id != payload.order_item_id:
        raise bad_request("Purchase verification returned wrong order item")
    if purchase.product_id != product_id:
        raise bad_request("Order item does not belong to this product")
    sku = await get_sku_with_product(db, purchase.sku_id)
    if sku is None or sku.product_id != product_id:
        raise bad_request("Order item SKU does not belong to this product")

    review = ProductReview(
        user_id=user_id,
        product_id=product_id,
        sku_id=sku.id,
        order_item_id=payload.order_item_id,
        rating=payload.rating,
        content=payload.content,
        is_anonymous=payload.is_anonymous,
    )
    review.sku = sku
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return _serialize_review(review)
