import logging
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import bad_request, conflict, not_found
from models.merchant import Merchant, MerchantFollow
from models.base import utc_now
from models.product import Product, ProductFavorite, ProductImage, ProductSku, ProductStatus
from settings.config import get_settings
from repository.product_repository import (
    category_has_children,
    get_category_by_id,
    get_product_by_id,
    get_product_for_update,
    get_public_product_by_id,
    get_sku_by_code,
    list_enabled_categories,
    list_enabled_category_ids,
    list_products_by_merchant,
    list_products_by_status,
    list_public_products,
    search_sale_products,
)
from schemas.product_schema import (
    ProductCreate,
    ProductDetailResponse,
    ProductFavoriteListResponse,
    ProductImageInput,
    ProductImageResponse,
    ProductMerchantSummary,
    ProductListResponse,
    ProductSkuResponse,
    ProductSummaryResponse,
    ProductSkuUpsert,
    ProductUpdate,
)


logger = logging.getLogger(__name__)


def _enabled_skus(product: Product) -> list[ProductSku]:
    return [sku for sku in product.skus if sku.is_enabled]


def _product_detail(
    product: Product,
    *,
    in_stock_skus_only: bool = False,
    include_disabled_skus: bool = False,
    merchant: Merchant | None = None,
    favorited_by_me: bool = False,
    following_merchant: bool = False,
) -> ProductDetailResponse:
    skus = list(product.skus) if include_disabled_skus else _enabled_skus(product)
    if in_stock_skus_only:
        skus = [sku for sku in skus if sku.stock > 0]
    return ProductDetailResponse(
        id=product.id,
        merchant_id=product.merchant_id,
        category_id=product.category_id,
        brand=product.brand,
        title=product.title,
        cover_image=product.cover_image,
        price=product.price,
        original_price=product.original_price,
        stock=product.stock,
        status=product.status,
        description=product.description,
        applicable_pet_type=product.applicable_pet_type,
        skus=[ProductSkuResponse.model_validate(sku) for sku in skus],
        images=[ProductImageResponse.model_validate(image) for image in product.images],
        merchant=ProductMerchantSummary(
            id=merchant.id,
            owner_user_id=merchant.owner_user_id,
            shop_name=merchant.shop_name,
            status=merchant.status,
        ) if merchant else None,
        favorited_by_me=favorited_by_me,
        following_merchant=following_merchant,
        audit_reason=product.audit_reason,
        submitted_at=product.submitted_at,
        audited_at=product.audited_at,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _build_images(
    product_id: int | None,
    payloads: list[ProductImageInput],
) -> list[ProductImage]:
    primary_count = sum(item.is_primary for item in payloads)
    if primary_count > 1:
        raise bad_request("Only one primary product image is allowed")
    return [
        ProductImage(
            product_id=product_id,
            image_url=item.image_url,
            sort_order=item.sort_order,
            is_primary=item.is_primary or (primary_count == 0 and index == 0),
        )
        for index, item in enumerate(payloads)
    ]


def _product_image_urls(product: Product) -> set[str]:
    urls = {image.image_url for image in product.images if image.image_url}
    if product.cover_image:
        urls.add(product.cover_image)
    return urls


def _generated_upload_path(url: str) -> Path | None:
    if not url.startswith("/generated/uploads/"):
        return None
    relative_text = unquote(url.removeprefix("/generated/"))
    relative_path = PurePosixPath(relative_text)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return None

    settings = get_settings()
    uploads_root = (settings.public_asset_path / "uploads").resolve()
    path = (settings.public_asset_path / Path(*relative_path.parts)).resolve()
    try:
        path.relative_to(uploads_root)
    except ValueError:
        return None
    return path


async def _is_product_image_url_referenced(db: AsyncSession, url: str) -> bool:
    image_reference = await db.scalar(
        select(ProductImage.id).where(ProductImage.image_url == url).limit(1)
    )
    if image_reference is not None:
        return True
    cover_reference = await db.scalar(
        select(Product.id).where(Product.cover_image == url).limit(1)
    )
    return cover_reference is not None


async def _cleanup_replaced_generated_product_images(
    db: AsyncSession,
    old_urls: set[str],
    new_urls: set[str],
) -> None:
    for url in sorted(old_urls - new_urls):
        path = _generated_upload_path(url)
        if path is None:
            continue
        if await _is_product_image_url_referenced(db, url):
            continue
        try:
            if path.exists() and path.is_file():
                path.unlink()
        except OSError as exc:
            logger.warning(
                "product_image_cleanup_failed",
                extra={
                    "image_url": url,
                    "path": str(path),
                    "exception_type": type(exc).__name__,
                    "error": str(exc),
                },
            )


async def _ensure_sku_code_available(
    db: AsyncSession,
    sku_code: str,
    sku_id: int | None = None,
) -> None:
    existing = await get_sku_by_code(db, sku_code)
    if existing is not None and existing.id != sku_id:
        raise conflict("SKU code already exists")


async def _build_new_skus(
    db: AsyncSession,
    payloads: list[ProductSkuUpsert],
) -> list[ProductSku]:
    seen_codes: set[str] = set()
    skus: list[ProductSku] = []
    for payload in payloads:
        if payload.id is not None:
            raise bad_request("New product SKU must not include id")
        if payload.sku_code in seen_codes:
            raise conflict("Duplicate SKU code in request")
        seen_codes.add(payload.sku_code)
        await _ensure_sku_code_available(db, payload.sku_code)
        skus.append(ProductSku(**payload.model_dump(exclude={"id"})))
    return skus


async def _upsert_skus(
    db: AsyncSession,
    product: Product,
    payloads: list[ProductSkuUpsert],
) -> None:
    existing_by_id = {sku.id: sku for sku in product.skus}
    seen_ids: set[int] = set()
    seen_codes: set[str] = set()
    for payload in payloads:
        if payload.sku_code in seen_codes:
            raise conflict("Duplicate SKU code in request")
        seen_codes.add(payload.sku_code)
        if payload.id is None:
            await _ensure_sku_code_available(db, payload.sku_code)
            product.skus.append(
                ProductSku(
                    product_id=product.id,
                    **payload.model_dump(exclude={"id"}),
                )
            )
            continue
        if payload.id in seen_ids:
            raise bad_request("Duplicate SKU id in request")
        seen_ids.add(payload.id)
        sku = existing_by_id.get(payload.id)
        if sku is None:
            raise not_found("Product SKU not found")
        await _ensure_sku_code_available(db, payload.sku_code, sku.id)
        for field, value in payload.model_dump(exclude={"id"}).items():
            setattr(sku, field, value)


def _sync_product_aggregates(product: Product) -> None:
    enabled_skus = [sku for sku in product.skus if sku.is_enabled]
    product.stock = sum(sku.stock for sku in enabled_skus)
    if enabled_skus:
        product.price = min(sku.price for sku in enabled_skus)
        original_prices = [
            sku.original_price
            for sku in enabled_skus
            if sku.original_price is not None
        ]
        product.original_price = min(original_prices) if original_prices else None
    else:
        product.price = 0
        product.original_price = None

    primary_images = [image for image in product.images if image.is_primary]
    if len(primary_images) > 1:
        raise bad_request("Only one primary product image is allowed")
    if product.images and not primary_images:
        product.images[0].is_primary = True
        primary_images = [product.images[0]]
    product.cover_image = primary_images[0].image_url if primary_images else None


def _ensure_product_ready_for_audit(product: Product) -> None:
    if not product.category.is_enabled:
        raise bad_request("Product category is disabled")
    if not any(sku.is_enabled for sku in product.skus):
        raise bad_request("At least one enabled SKU is required")
    if not product.images:
        raise bad_request("At least one product image is required")


async def get_categories(db: AsyncSession):
    return await list_enabled_categories(db)


async def _ensure_leaf_category(db: AsyncSession, category_id: int):
    category = await get_category_by_id(db, category_id)
    if category is None or not category.is_enabled:
        raise bad_request("Product category is unavailable")
    if await category_has_children(db, category.id):
        raise bad_request("Please select a leaf product category")
    return category


async def _category_subtree_ids(db: AsyncSession, category_id: int | None) -> list[int] | None:
    if category_id is None:
        return None
    category_rows = await list_enabled_category_ids(db)
    enabled_ids = {item_id for item_id, _ in category_rows}
    if category_id not in enabled_ids:
        return []

    children_by_parent: dict[int | None, list[int]] = {}
    for item_id, parent_id in category_rows:
        children_by_parent.setdefault(parent_id, []).append(item_id)

    ids: list[int] = []
    stack = [category_id]
    while stack:
        current_id = stack.pop()
        ids.append(current_id)
        stack.extend(children_by_parent.get(current_id, []))
    return ids


async def get_products(
    db: AsyncSession,
    *,
    keyword: str | None,
    brand_keyword: str | None,
    category_id: int | None,
    pet_type: str | None,
    min_price: int | None,
    max_price: int | None,
    page: int,
    page_size: int,
    sort: str,
) -> ProductListResponse:
    category_ids = await _category_subtree_ids(db, category_id)
    products, total = await list_public_products(
        db,
        keyword=keyword,
        brand_keyword=brand_keyword,
        category_ids=category_ids,
        pet_type=pet_type,
        min_price=min_price,
        max_price=max_price,
        page=page,
        page_size=page_size,
        sort=sort,
    )
    return ProductListResponse(items=products, total=total, page=page, page_size=page_size)


async def get_product_detail(
    db: AsyncSession,
    product_id: int,
    current_user_id: int | None = None,
) -> ProductDetailResponse:
    product = await get_public_product_by_id(db, product_id)
    if product is None:
        raise not_found("Product not found")
    merchant = await db.get(Merchant, product.merchant_id)
    favorited_by_me = False
    following_merchant = False
    if current_user_id is not None:
        favorited_by_me = await db.scalar(
            select(ProductFavorite.id).where(
                ProductFavorite.user_id == current_user_id,
                ProductFavorite.product_id == product.id,
            )
        ) is not None
        following_merchant = await db.scalar(
            select(MerchantFollow.id).where(
                MerchantFollow.user_id == current_user_id,
                MerchantFollow.merchant_id == product.merchant_id,
            )
        ) is not None
    return _product_detail(
        product,
        merchant=merchant,
        favorited_by_me=favorited_by_me,
        following_merchant=following_merchant,
    )


async def set_product_favorite(db: AsyncSession, user_id: int, product_id: int, enabled: bool) -> None:
    product = await get_public_product_by_id(db, product_id)
    if product is None:
        raise not_found("Product not found")
    existing = await db.scalar(
        select(ProductFavorite).where(
            ProductFavorite.user_id == user_id,
            ProductFavorite.product_id == product_id,
        )
    )
    if enabled and existing is None:
        db.add(ProductFavorite(user_id=user_id, product_id=product_id))
    elif not enabled and existing is not None:
        await db.delete(existing)
    await db.commit()


async def list_product_favorites(
    db: AsyncSession,
    user_id: int,
    *,
    page: int = 1,
    page_size: int = 20,
) -> ProductFavoriteListResponse:
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 100)
    filters = [
        ProductFavorite.user_id == user_id,
        Product.status == ProductStatus.ON_SALE.value,
    ]
    total = int(
        (
            await db.scalar(
                select(func.count(ProductFavorite.id))
                .join(Product, Product.id == ProductFavorite.product_id)
                .where(*filters)
            )
        )
        or 0
    )
    result = await db.execute(
        select(Product)
        .join(ProductFavorite, ProductFavorite.product_id == Product.id)
        .where(*filters)
        .order_by(ProductFavorite.created_at.desc(), ProductFavorite.id.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
    )
    return ProductFavoriteListResponse(
        items=[ProductSummaryResponse.model_validate(item) for item in result.scalars()],
        total=total,
        page=safe_page,
        page_size=safe_page_size,
    )


async def set_merchant_follow(db: AsyncSession, user_id: int, merchant_id: int, enabled: bool) -> None:
    merchant = await db.get(Merchant, merchant_id)
    if merchant is None or merchant.status != "approved":
        raise not_found("Merchant not found")
    if merchant.owner_user_id == user_id:
        raise bad_request("不能关注自己的店铺")
    existing = await db.scalar(
        select(MerchantFollow).where(
            MerchantFollow.user_id == user_id,
            MerchantFollow.merchant_id == merchant_id,
        )
    )
    if enabled and existing is None:
        db.add(MerchantFollow(user_id=user_id, merchant_id=merchant_id))
    elif not enabled and existing is not None:
        await db.delete(existing)
    await db.commit()


async def get_products_for_merchant(
    db: AsyncSession,
    merchant_id: int,
    *,
    offset: int = 0,
    limit: int = 100,
) -> list[Product]:
    return await list_products_by_merchant(
        db,
        merchant_id,
        offset=offset,
        limit=limit,
    )


async def get_product_for_merchant(
    db: AsyncSession,
    merchant_id: int,
    product_id: int,
) -> ProductDetailResponse:
    product = await get_product_by_id(db, product_id)
    if product is None or product.merchant_id != merchant_id:
        raise not_found("Product not found")
    return _product_detail(product, include_disabled_skus=True)


async def create_merchant_product(
    db: AsyncSession,
    merchant_id: int,
    payload: ProductCreate,
) -> ProductDetailResponse:
    category = await _ensure_leaf_category(db, payload.category_id)
    skus = await _build_new_skus(db, payload.skus)
    product = Product(
        merchant_id=merchant_id,
        category_id=category.id,
        brand=payload.brand,
        title=payload.title,
        description=payload.description,
        applicable_pet_type=payload.applicable_pet_type,
        price=0,
        stock=0,
        status=ProductStatus.DRAFT.value,
    )
    product.category = category
    product.skus = skus
    product.images = _build_images(None, payload.images)
    _sync_product_aggregates(product)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return _product_detail(product, include_disabled_skus=True)


async def update_merchant_product(
    db: AsyncSession,
    merchant_id: int,
    product_id: int,
    payload: ProductUpdate,
) -> ProductDetailResponse:
    product = await get_product_for_update(db, product_id)
    if product is None or product.merchant_id != merchant_id:
        raise not_found("Product not found")
    if product.status not in {
        ProductStatus.DRAFT.value,
        ProductStatus.REJECTED.value,
        ProductStatus.OFF_SHELF.value,
    }:
        raise bad_request("Product cannot be modified in current status")

    old_image_urls = _product_image_urls(product) if payload.images is not None else set()
    data = payload.model_dump(exclude_unset=True, exclude={"skus", "images", "category_id"})
    for field, value in data.items():
        setattr(product, field, value)
    if payload.category_id is not None:
        category = await _ensure_leaf_category(db, payload.category_id)
        product.category_id = category.id
        product.category = category
    if payload.skus is not None:
        await _upsert_skus(db, product, payload.skus)
    if payload.images is not None:
        product.images = _build_images(product.id, payload.images)

    _sync_product_aggregates(product)
    product.status = ProductStatus.DRAFT.value
    product.audit_reason = None
    product.submitted_at = None
    product.audited_at = None
    await db.commit()
    if payload.images is not None:
        await _cleanup_replaced_generated_product_images(db, old_image_urls, _product_image_urls(product))
    await db.refresh(product)
    return _product_detail(product, include_disabled_skus=True)


async def submit_product_for_audit(
    db: AsyncSession,
    merchant_id: int,
    product_id: int,
    *,
    commit: bool = True,
) -> ProductDetailResponse:
    product = await get_product_for_update(db, product_id)
    if product is None or product.merchant_id != merchant_id:
        raise not_found("Product not found")
    if product.status not in {
        ProductStatus.DRAFT.value,
        ProductStatus.REJECTED.value,
        ProductStatus.OFF_SHELF.value,
    }:
        raise bad_request("Product cannot be submitted in current status")
    _ensure_product_ready_for_audit(product)
    _sync_product_aggregates(product)
    product.status = ProductStatus.PENDING.value
    product.audit_reason = None
    product.submitted_at = utc_now()
    product.audited_at = None
    if commit:
        await db.commit()
        await db.refresh(product)
    else:
        await db.flush()
    return _product_detail(product, include_disabled_skus=True)


async def get_pending_products_for_audit(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 100)
    products, total = await list_products_by_status(
        db,
        ProductStatus.PENDING.value,
        page=safe_page,
        page_size=safe_page_size,
    )
    return {
        "items": [
            _product_detail(product, include_disabled_skus=True).model_dump()
            for product in products
        ],
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }


async def set_merchant_product_sale_status(
    db: AsyncSession,
    merchant_id: int,
    product_id: int,
    *,
    on_sale: bool,
    commit: bool = True,
) -> ProductDetailResponse:
    product = await get_product_for_update(db, product_id)
    if product is None or product.merchant_id != merchant_id:
        raise not_found("Product not found")
    target = ProductStatus.ON_SALE.value if on_sale else ProductStatus.OFF_SHELF.value
    expected = ProductStatus.OFF_SHELF.value if on_sale else ProductStatus.ON_SALE.value
    if product.status != expected:
        raise bad_request("Product cannot change sale status in current status")
    if on_sale:
        if product.audited_at is None or product.audit_reason:
            raise bad_request("Only an approved product can be put on sale")
        _ensure_product_ready_for_audit(product)
        _sync_product_aggregates(product)
    product.status = target
    if commit:
        await db.commit()
        await db.refresh(product)
    else:
        await db.flush()
    return _product_detail(product, include_disabled_skus=True)


async def update_merchant_product_discount(
    db: AsyncSession,
    merchant_id: int,
    product_id: int,
    sku_prices: dict[int, int],
    *,
    commit: bool = True,
) -> ProductDetailResponse:
    if not sku_prices:
        raise bad_request("At least one SKU price is required")
    product = await get_product_for_update(db, product_id)
    if product is None or product.merchant_id != merchant_id:
        raise not_found("Product not found")
    if product.status not in {ProductStatus.ON_SALE.value, ProductStatus.OFF_SHELF.value}:
        raise bad_request("Product discount cannot be changed in current status")
    sku_by_id = {sku.id: sku for sku in product.skus}
    for sku_id, price in sku_prices.items():
        sku = sku_by_id.get(sku_id)
        if sku is None:
            raise not_found("Product SKU not found")
        if price < 0:
            raise bad_request("SKU price cannot be negative")
        reference_price = sku.original_price if sku.original_price is not None else sku.price
        if price > reference_price:
            raise bad_request("Discount price cannot exceed original price")
        if sku.original_price is None:
            sku.original_price = sku.price
        sku.price = price
    _sync_product_aggregates(product)
    if commit:
        await db.commit()
        await db.refresh(product)
    else:
        await db.flush()
    return _product_detail(product, include_disabled_skus=True)


async def get_product_audit_detail(
    db: AsyncSession,
    product_id: int,
) -> dict:
    product = await get_product_by_id(db, product_id)
    if product is None:
        raise not_found("Product not found")
    return _product_detail(product, include_disabled_skus=True).model_dump()


async def update_product_audit_status(
    db: AsyncSession,
    product_id: int,
    status: str,
    reason: str | None,
    *,
    commit: bool = True,
) -> None:
    product = await get_product_for_update(db, product_id)
    if product is None:
        raise not_found("Product not found")
    allowed_transitions = {
        ProductStatus.PENDING.value: {
            ProductStatus.ON_SALE.value,
            ProductStatus.REJECTED.value,
        },
        ProductStatus.ON_SALE.value: {ProductStatus.OFF_SHELF.value},
    }
    if status not in allowed_transitions.get(product.status, set()):
        raise bad_request("Invalid product audit status transition")
    normalized_reason = reason.strip() if reason else None
    if status == ProductStatus.REJECTED.value and not normalized_reason:
        raise bad_request("Rejection reason is required")
    if status == ProductStatus.ON_SALE.value:
        _ensure_product_ready_for_audit(product)
        _sync_product_aggregates(product)
        product.audit_reason = None
    else:
        product.audit_reason = normalized_reason
    product.status = status
    product.audited_at = utc_now()
    if commit:
        await db.commit()
    else:
        await db.flush()


async def get_product_for_agent(db: AsyncSession, product_id: int) -> dict:
    product = await get_public_product_by_id(db, product_id)
    if product is None or product.stock <= 0:
        raise not_found("Product not found")
    detail = _product_detail(product, in_stock_skus_only=True)
    if not detail.skus:
        raise not_found("Product not found")
    return detail.model_dump()


async def search_products_for_agent(
    db: AsyncSession,
    query: str,
    pet_type: str | None,
    limit: int = 10,
) -> list[dict]:
    safe_limit = max(1, min(limit, 50))
    products = await search_sale_products(db, query, pet_type, safe_limit)
    return [
        _product_detail(product, in_stock_skus_only=True).model_dump()
        for product in products
    ]
