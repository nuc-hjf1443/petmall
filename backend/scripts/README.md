# Backend Scripts

Place one-off local scripts here, such as admin creation, seed data, and maintenance helpers.

Scripts must read configuration from `backend/settings/` or environment variables. Do not hardcode passwords, tokens, certificates, or production addresses.

## Seed product categories

Run this after database migrations to initialize `product_category`:

```bash
python backend/scripts/seed_categories.py
```

The script is idempotent. It creates missing categories and updates parent, sort order, and enabled status for existing categories with the same name.
