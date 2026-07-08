from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.product import (
    Product,
    ProductCategory,
    ProductReview,
    ProductSku,
    ProductStatus,
)
from models.order import Order, OrderItem, OrderStatus


async def list_enabled_categories(db: AsyncSession) -> list[ProductCategory]:
    result = await db.execute(
        select(ProductCategory)
        .where(ProductCategory.is_enabled.is_(True))
        .order_by(ProductCategory.sort_order, ProductCategory.id)
    )
    return list(result.scalars().all())


async def list_public_products(
    db: AsyncSession,
    *,
    keyword: str | None,
    brand_keyword: str | None,
    category_ids: list[int] | None,
    pet_type: str | None,
    min_price: int | None,
    max_price: int | None,
    page: int,
    page_size: int,
    sort: str,
) -> tuple[list[Product], int]:
    filters = [
        Product.status == ProductStatus.ON_SALE.value,
        ProductCategory.is_enabled.is_(True),
    ]
    if keyword:
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(Product.title.ilike(pattern), Product.description.ilike(pattern)))
    if brand_keyword:
        pattern = f"%{brand_keyword.strip()}%"
        filters.append(
            or_(
                Product.brand.ilike(pattern),
                Product.title.ilike(pattern),
                Product.description.ilike(pattern),
            )
        )
    if category_ids is not None:
        filters.append(Product.category_id.in_(category_ids))
    if pet_type:
        filters.append(Product.applicable_pet_type == pet_type.strip())
    if min_price is not None:
        filters.append(Product.price >= min_price)
    if max_price is not None:
        filters.append(Product.price <= max_price)

    total = await db.scalar(
        select(func.count(Product.id))
        .join(ProductCategory, ProductCategory.id == Product.category_id)
        .where(*filters)
    )
    sales_statuses = [
        OrderStatus.PAID.value,
        OrderStatus.PENDING_SHIPMENT.value,
        OrderStatus.SHIPPED.value,
        OrderStatus.PENDING_RECEIPT.value,
        OrderStatus.COMPLETED.value,
    ]
    sales_subquery = (
        select(
            OrderItem.product_id.label("product_id"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("sales_count"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status.in_(sales_statuses))
        .group_by(OrderItem.product_id)
        .subquery()
    )
    order_by = {
        "newest": [Product.created_at.desc(), Product.id.desc()],
        "price_asc": [Product.price.asc(), Product.id.desc()],
        "price_desc": [Product.price.desc(), Product.id.desc()],
        "sales": [desc(func.coalesce(sales_subquery.c.sales_count, 0)), Product.updated_at.desc(), Product.id.desc()],
    }.get(sort, [Product.updated_at.desc(), Product.id.desc()])

    result = await db.execute(
        select(Product)
        .join(ProductCategory, ProductCategory.id == Product.category_id)
        .outerjoin(sales_subquery, sales_subquery.c.product_id == Product.id)
        .where(*filters)
        .order_by(*order_by)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), int(total or 0)


async def get_product_by_id(db: AsyncSession, product_id: int) -> Product | None:
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.skus),
            selectinload(Product.images),
        )
        .where(Product.id == product_id)
    )
    return result.scalar_one_or_none()


async def get_public_product_by_id(db: AsyncSession, product_id: int) -> Product | None:
    result = await db.execute(
        select(Product)
        .join(ProductCategory, ProductCategory.id == Product.category_id)
        .options(
            selectinload(Product.category),
            selectinload(Product.skus),
            selectinload(Product.images),
        )
        .where(
            Product.id == product_id,
            Product.status == ProductStatus.ON_SALE.value,
            ProductCategory.is_enabled.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def get_sku_with_product(db: AsyncSession, sku_id: int) -> ProductSku | None:
    result = await db.execute(
        select(ProductSku)
        .options(
            selectinload(ProductSku.product).selectinload(Product.category),
        )
        .where(ProductSku.id == sku_id)
    )
    return result.scalar_one_or_none()


async def list_products_by_merchant(
    db: AsyncSession,
    merchant_id: int,
    *,
    offset: int = 0,
    limit: int = 100,
) -> list[Product]:
    result = await db.execute(
        select(Product)
        .where(Product.merchant_id == merchant_id)
        .order_by(Product.updated_at.desc(), Product.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_products_by_status(
    db: AsyncSession,
    status: str,
    *,
    page: int,
    page_size: int,
) -> tuple[list[Product], int]:
    total = int(
        (await db.scalar(select(func.count(Product.id)).where(Product.status == status))) or 0
    )
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.skus),
            selectinload(Product.images),
        )
        .where(Product.status == status)
        .order_by(Product.submitted_at, Product.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().unique().all()), total


async def get_category_by_id(
    db: AsyncSession,
    category_id: int,
) -> ProductCategory | None:
    return await db.get(ProductCategory, category_id)


async def category_has_children(
    db: AsyncSession,
    category_id: int,
) -> bool:
    child_id = await db.scalar(
        select(ProductCategory.id)
        .where(
            ProductCategory.parent_id == category_id,
            ProductCategory.is_enabled.is_(True),
        )
        .limit(1)
    )
    return child_id is not None


async def list_enabled_category_ids(db: AsyncSession) -> list[tuple[int, int | None]]:
    result = await db.execute(
        select(ProductCategory.id, ProductCategory.parent_id)
        .where(ProductCategory.is_enabled.is_(True))
        .order_by(ProductCategory.sort_order, ProductCategory.id)
    )
    return list(result.all())


async def get_product_for_update(
    db: AsyncSession,
    product_id: int,
) -> Product | None:
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.skus),
            selectinload(Product.images),
        )
        .where(Product.id == product_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def get_sku_by_code(
    db: AsyncSession,
    sku_code: str,
) -> ProductSku | None:
    result = await db.execute(
        select(ProductSku).where(ProductSku.sku_code == sku_code)
    )
    return result.scalar_one_or_none()


async def get_product_review_by_order_item(
    db: AsyncSession,
    order_item_id: int,
) -> ProductReview | None:
    result = await db.execute(
        select(ProductReview).where(ProductReview.order_item_id == order_item_id)
    )
    return result.scalar_one_or_none()


async def list_product_reviews(
    db: AsyncSession,
    product_id: int,
    *,
    page: int,
    page_size: int,
) -> tuple[list[ProductReview], int, float | None]:
    filters = [
        ProductReview.product_id == product_id,
        ProductReview.is_deleted.is_(False),
    ]
    summary = (
        await db.execute(
            select(
                func.count(ProductReview.id),
                func.avg(ProductReview.rating),
            ).where(*filters)
        )
    ).one()
    result = await db.execute(
        select(ProductReview)
        .options(selectinload(ProductReview.sku))
        .where(*filters)
        .order_by(ProductReview.created_at.desc(), ProductReview.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    average = float(summary[1]) if summary[1] is not None else None
    return list(result.scalars().all()), int(summary[0] or 0), average


async def search_sale_products(
    db: AsyncSession,
    query: str,
    pet_type: str | None,
    limit: int,
) -> list[Product]:
    filters = [
        Product.status == ProductStatus.ON_SALE.value,
        ProductCategory.is_enabled.is_(True),
        Product.stock > 0,
    ]
    if query.strip():
        pattern = f"%{query.strip()}%"
        filters.append(or_(Product.title.ilike(pattern), Product.description.ilike(pattern)))
    if pet_type:
        filters.append(
            or_(
                Product.applicable_pet_type == pet_type.strip(),
                Product.applicable_pet_type.is_(None),
            )
        )
    result = await db.execute(
        select(Product)
        .join(ProductCategory, ProductCategory.id == Product.category_id)
        .join(ProductSku, ProductSku.product_id == Product.id)
        .options(
            selectinload(Product.category),
            selectinload(Product.skus),
            selectinload(Product.images),
        )
        .where(
            *filters,
            ProductSku.is_enabled.is_(True),
            ProductSku.stock > 0,
        )
        .distinct()
        .order_by(Product.updated_at.desc(), Product.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
