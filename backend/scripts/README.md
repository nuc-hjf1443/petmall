# Backend Scripts

Place one-off local scripts here, such as admin creation, seed data, and maintenance helpers.

Scripts must read configuration from `backend/settings/` or environment variables. Do not hardcode passwords, tokens, certificates, or production addresses.

## Seed product categories

Run this after database migrations to initialize `product_category`:

```bash
python backend/scripts/seed_categories.py
```

The script is idempotent. It creates missing categories and updates parent, sort order, and enabled status for existing categories with the same name.

## Seed category-covered products

Generate editable seed data from the category tree:

```bash
python backend/scripts/generate_category_product_seed.py
```

Import the generated products:

```bash
python backend/scripts/seed_products_from_categories.py
```

The import script is idempotent. It reads `backend/scripts/data/category_products_seed.json`, creates or updates products by the first SKU code, and adds SKUs/images for every product. Use `--dry-run` to validate without committing:

```bash
python backend/scripts/seed_products_from_categories.py --dry-run
```
