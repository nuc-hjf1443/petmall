import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.database import AsyncSessionLocal, engine
from models.product import Product, ProductCategory, ProductImage, ProductSku, ProductStatus
from scripts.seed_categories import seed_categories


DEFAULT_DATA_FILE = Path(__file__).resolve().parent / "data" / "category_products_seed.json"


def _load_seed_products(data_file: Path) -> list[dict[str, Any]]:
    with data_file.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("Seed product data must be a list")
    return data


def _copy_fields(target: Any, data: dict[str, Any], fields: tuple[str, ...]) -> bool:
    changed = False
    for field in fields:
        if field in data and getattr(target, field) != data[field]:
            setattr(target, field, data[field])
            changed = True
    return changed


async def _category_by_name(db: AsyncSession) -> dict[str, ProductCategory]:
    result = await db.execute(select(ProductCategory))
    return {category.name: category for category in result.scalars().all()}


async def _find_product_by_primary_sku(db: AsyncSession, sku_code: str) -> Product | None:
    sku = await db.scalar(select(ProductSku).where(ProductSku.sku_code == sku_code))
    if sku is None:
        return None
    return await db.scalar(
        select(Product)
        .options(selectinload(Product.skus), selectinload(Product.images))
        .where(Product.id == sku.product_id)
    )


async def _upsert_skus(db: AsyncSession, product: Product, sku_payloads: list[dict[str, Any]]) -> tuple[int, int]:
    created = 0
    updated = 0
    for payload in sku_payloads:
        sku = await db.scalar(select(ProductSku).where(ProductSku.sku_code == payload["sku_code"]))
        is_new = sku is None
        if sku is None:
            sku = ProductSku(product_id=product.id, sku_code=payload["sku_code"])
            db.add(sku)
            created += 1
        sku.product_id = product.id
        changed = _copy_fields(
            sku,
            payload,
            ("name", "specs", "price", "original_price", "stock", "is_enabled"),
        )
        updated += int(changed and not is_new)
    return created, updated


async def _upsert_images(db: AsyncSession, product: Product, image_urls: list[str]) -> tuple[int, int]:
    created = 0
    updated = 0
    for index, image_url in enumerate(image_urls, start=1):
        image = await db.scalar(
            select(ProductImage).where(
                ProductImage.product_id == product.id,
                ProductImage.image_url == image_url,
            )
        )
        is_new = image is None
        if image is None:
            image = ProductImage(product_id=product.id, image_url=image_url)
            db.add(image)
            created += 1
        changed = False
        if image.sort_order != index:
            image.sort_order = index
            changed = True
        is_primary = index == 1
        if image.is_primary != is_primary:
            image.is_primary = is_primary
            changed = True
        updated += int(changed and not is_new)
    return created, updated


async def seed_products(
    db: AsyncSession,
    products: list[dict[str, Any]],
    *,
    merchant_id: int,
    dry_run: bool = False,
) -> dict[str, int]:
    await seed_categories(db)
    categories = await _category_by_name(db)
    stats = {
        "products_created": 0,
        "products_updated": 0,
        "skus_created": 0,
        "skus_updated": 0,
        "images_created": 0,
        "images_updated": 0,
    }

    for item in products:
        category_name = item["category"]
        category = categories.get(category_name)
        if category is None:
            raise ValueError(f"Category not found: {category_name}")
        skus = item.get("skus") or []
        if not skus:
            raise ValueError(f"Product has no SKU payload: {item.get('title')}")

        product = await _find_product_by_primary_sku(db, skus[0]["sku_code"])
        is_new_product = product is None
        if product is None:
            product = Product(
                merchant_id=merchant_id,
                category_id=category.id,
                title=item["title"],
            )
            db.add(product)
            await db.flush()
            stats["products_created"] += 1

        changed = False
        if product.category_id != category.id:
            product.category_id = category.id
            changed = True
        if product.merchant_id != merchant_id:
            product.merchant_id = merchant_id
            changed = True
        changed = _copy_fields(
            product,
            {
                **item,
                "status": item.get("status") or ProductStatus.ON_SALE.value,
            },
            (
                "brand",
                "title",
                "cover_image",
                "price",
                "original_price",
                "stock",
                "status",
                "description",
                "applicable_pet_type",
            ),
        ) or changed
        stats["products_updated"] += int(changed and not is_new_product)
        await db.flush()

        sku_created, sku_updated = await _upsert_skus(db, product, skus)
        stats["skus_created"] += sku_created
        stats["skus_updated"] += sku_updated

        image_urls = item.get("images") or ([item["cover_image"]] if item.get("cover_image") else [])
        image_created, image_updated = await _upsert_images(db, product, image_urls)
        stats["images_created"] += image_created
        stats["images_updated"] += image_updated

    if dry_run:
        await db.rollback()
    else:
        await db.commit()
    return stats


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed category-covered mock products.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_FILE)
    parser.add_argument("--merchant-id", type=int, default=3001)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        products = _load_seed_products(args.data)
        async with AsyncSessionLocal() as db:
            stats = await seed_products(
                db,
                products,
                merchant_id=args.merchant_id,
                dry_run=args.dry_run,
            )
        print(
            "Seeded category products: "
            + ", ".join(f"{key}={value}" for key, value in stats.items())
            + f", dry_run={args.dry_run}"
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
