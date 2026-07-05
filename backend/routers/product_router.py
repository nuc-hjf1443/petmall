from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db
from models.user import User
from schemas.product_schema import (
    ProductCategoryResponse,
    ProductDetailResponse,
    ProductListResponse,
    ProductReviewCreate,
    ProductReviewListResponse,
    ProductReviewResponse,
)
from services.review_service import (
    ReviewPurchaseVerifier,
    create_product_review,
    get_product_reviews,
    get_review_purchase_verifier,
)
from services.product_service import get_categories, get_product_detail, get_products


router = APIRouter(tags=["products"])


@router.get("/categories", response_model=list[ProductCategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await get_categories(db)


@router.get("/products", response_model=ProductListResponse)
async def list_products(
    keyword: Annotated[str | None, Query(max_length=100)] = None,
    category_id: Annotated[int | None, Query(gt=0)] = None,
    pet_type: Annotated[str | None, Query(max_length=64)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> ProductListResponse:
    return await get_products(
        db,
        keyword=keyword,
        category_id=category_id,
        pet_type=pet_type,
        page=page,
        page_size=page_size,
    )


@router.get("/products/{product_id}", response_model=ProductDetailResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> ProductDetailResponse:
    return await get_product_detail(db, product_id)


@router.get(
    "/products/{product_id}/reviews",
    response_model=ProductReviewListResponse,
)
async def list_product_reviews(
    product_id: int,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> ProductReviewListResponse:
    return await get_product_reviews(
        db,
        product_id,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/products/{product_id}/reviews",
    response_model=ProductReviewResponse,
)
async def add_product_review(
    product_id: int,
    payload: ProductReviewCreate,
    current_user: User = Depends(get_current_user),
    verifier: ReviewPurchaseVerifier = Depends(get_review_purchase_verifier),
    db: AsyncSession = Depends(get_db),
) -> ProductReviewResponse:
    return await create_product_review(
        db,
        current_user.id,
        product_id,
        payload,
        verifier,
    )
