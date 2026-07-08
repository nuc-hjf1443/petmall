from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db, get_optional_current_user
from models.user import User
from schemas.product_schema import (
    ProductCategoryResponse,
    ProductDetailResponse,
    ProductFavoriteListResponse,
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
from services.product_service import (
    get_categories,
    get_product_detail,
    get_products,
    list_product_favorites,
    set_product_favorite,
)


router = APIRouter(tags=["products"])


@router.get("/categories", response_model=list[ProductCategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await get_categories(db)


@router.get("/products", response_model=ProductListResponse)
async def list_products(
    keyword: Annotated[str | None, Query(max_length=100)] = None,
    brand_keyword: Annotated[str | None, Query(max_length=100)] = None,
    category_id: Annotated[int | None, Query(gt=0)] = None,
    pet_type: Annotated[str | None, Query(max_length=64)] = None,
    min_price: Annotated[int | None, Query(ge=0)] = None,
    max_price: Annotated[int | None, Query(ge=0)] = None,
    sort: Annotated[str, Query(pattern="^(sales|newest|price_asc|price_desc)$")] = "sales",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> ProductListResponse:
    return await get_products(
        db,
        keyword=keyword,
        brand_keyword=brand_keyword,
        category_id=category_id,
        pet_type=pet_type,
        min_price=min_price,
        max_price=max_price,
        page=page,
        page_size=page_size,
        sort=sort,
    )


@router.get("/products/favorites", response_model=ProductFavoriteListResponse)
async def my_product_favorites(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductFavoriteListResponse:
    return await list_product_favorites(db, current_user.id, page=page, page_size=page_size)


@router.get("/products/{product_id}", response_model=ProductDetailResponse)
async def get_product(
    product_id: int,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductDetailResponse:
    return await get_product_detail(db, product_id, current_user.id if current_user else None)


@router.post("/products/{product_id}/favorite")
async def favorite_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await set_product_favorite(db, current_user.id, product_id, True)
    return {"message": "Product favorited"}


@router.delete("/products/{product_id}/favorite")
async def unfavorite_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await set_product_favorite(db, current_user.id, product_id, False)
    return {"message": "Product unfavorited"}


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
