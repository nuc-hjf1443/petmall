import json
import re
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.seed_categories import CATEGORY_TREE


DATA_DIR = Path(__file__).resolve().parent / "data"
DOCS_DIR = BACKEND_DIR.parent / "docs"


BRAND_BY_TOP_INDEX = {
    1: ["鲜宠工坊", "毛孩子厨房", "贝乐鲜", "宠爱严选"],
    2: ["小爪生活", "宠爱有家", "PawHome", "安心宠居"],
    3: ["净爪研究所", "毛发管家", "柔护星球", "宠美实验室"],
    4: ["康宠守护", "宠健优选", "安心兽护", "益宠计划"],
    5: ["小爪衣橱", "萌宠造物", "PawStyle", "宠趣定制"],
    6: ["安心领养", "萌友之家", "良宠计划", "宠缘平台"],
    7: ["到家宠护", "邻里宠服", "安心托管", "宠伴服务"],
}

DETAIL_BY_TOP_INDEX = {
    1: ["低敏配方", "高蛋白配方", "日常营养款", "肠胃友好款"],
    2: ["耐用升级款", "易清洗款", "家用基础款", "智能便捷款"],
    3: ["温和护理款", "敏感肌适用款", "门店同款", "日常护理款"],
    4: ["家庭常备款", "兽医建议备用", "日常护理款", "健康管理款"],
    5: ["舒适亲肤款", "四季通用款", "轻量设计款", "拍照出片款"],
    6: ["健康档案齐全", "新手友好", "已做基础检查", "可预约看宠"],
    7: ["标准服务", "进阶服务", "预约套餐", "到店/到家可选"],
}

PRICE_BY_TOP_INDEX = {
    1: (3900, 39900),
    2: (2900, 69900),
    3: (1900, 29900),
    4: (2900, 49900),
    5: (1900, 19900),
    6: (0, 199900),
    7: (3900, 59900),
}

SKU_UNITS_BY_TOP_INDEX = {
    1: [("体验装", {"size": "trial"}), ("家庭装", {"size": "family"})],
    2: [("标准款", {"variant": "standard"}), ("升级款", {"variant": "plus"})],
    3: [("单件装", {"count": "1"}), ("组合装", {"count": "bundle"})],
    4: [("基础装", {"variant": "basic"}), ("加强装", {"variant": "pro"})],
    5: [("S/M 码", {"size": "S-M"}), ("L/XL 码", {"size": "L-XL"})],
    6: [("预约咨询", {"service": "consult"}), ("档案核验", {"service": "profile-check"})],
    7: [("单次服务", {"count": "1"}), ("3 次套餐", {"count": "3"})],
}

TOP_CODE_BY_INDEX = {
    1: "FOOD",
    2: "SUPPLY",
    3: "GROOM",
    4: "HEALTH",
    5: "STYLE",
    6: "ADOPT",
    7: "SERVICE",
}

CAT_WORDS = ("猫", "幼猫", "成猫", "老年猫", "猫舍", "猫砂", "猫条", "逗猫")
DOG_WORDS = ("狗", "犬", "幼犬", "成犬", "老年犬", "犬舍", "狗粮", "牵引", "遛狗")
FREE_SERVICE_WORDS = ("免费领养", "公益领养", "救助领养")


def pet_type_for(*names: str) -> str | None:
    text = "".join(names)
    has_cat = any(word in text for word in CAT_WORDS)
    has_dog = any(word in text for word in DOG_WORDS)
    if has_cat and not has_dog:
        return "cat"
    if has_dog and not has_cat:
        return "dog"
    return None


def base_price(top_index: int, leaf: str, leaf_count: int, variant: int) -> int:
    if leaf in FREE_SERVICE_WORDS:
        return 0
    low, high = PRICE_BY_TOP_INDEX[top_index]
    spread = max(1, high - low)
    value = low + ((leaf_count * 1379 + variant * 2300) % spread)
    return int(round(value / 100.0) * 100)


def stock_for(top_index: int, leaf_count: int, variant: int) -> int:
    if top_index in {6, 7}:
        return 20 + ((leaf_count + variant) % 30)
    return 60 + ((leaf_count * 7 + variant * 13) % 180)


def product_title(brand: str, leaf: str, detail: str, applicable_pet_type: str | None) -> str:
    title = f"{brand}{leaf}{detail}"
    if applicable_pet_type == "dog" and "狗" not in title and "犬" not in title:
        return f"狗狗{title}"
    if applicable_pet_type == "cat" and "猫" not in title:
        return f"猫咪{title}"
    return title


def build_seed_products() -> list[dict]:
    products: list[dict] = []
    leaf_count = 0
    for top_index, (top, second_level_categories) in enumerate(CATEGORY_TREE, start=1):
        for second, third_level_names in second_level_categories:
            for leaf in third_level_names:
                leaf_count += 1
                applicable_pet_type = pet_type_for(top, second, leaf)
                brands = BRAND_BY_TOP_INDEX[top_index]
                details = DETAIL_BY_TOP_INDEX[top_index]
                for variant in (1, 2):
                    brand = brands[(leaf_count + variant) % len(brands)]
                    detail = details[(leaf_count + variant) % len(details)]
                    price = base_price(top_index, leaf, leaf_count, variant)
                    original_price = int(price * 1.18) if price else 0
                    stock = stock_for(top_index, leaf_count, variant)
                    code_prefix = f"CAT-{TOP_CODE_BY_INDEX[top_index]}-{leaf_count:03d}-{variant}"
                    cover = f"https://picsum.photos/seed/petmall-{leaf_count}-{variant}/640/480"
                    skus = []
                    for sku_index, (sku_name, specs) in enumerate(SKU_UNITS_BY_TOP_INDEX[top_index], start=1):
                        sku_price = price + (sku_index - 1) * max(0, int(price * 0.22))
                        skus.append(
                            {
                                "sku_code": f"{code_prefix}-SKU{sku_index}",
                                "name": sku_name,
                                "specs": {
                                    **specs,
                                    "category": leaf,
                                    "path": f"{top}/{second}/{leaf}",
                                },
                                "price": sku_price,
                                "original_price": int(sku_price * 1.18) if sku_price else 0,
                                "stock": max(1, stock - sku_index * 3),
                                "is_enabled": True,
                            }
                        )
                    products.append(
                        {
                            "category_path": [top, second, leaf],
                            "category": leaf,
                            "brand": brand,
                            "title": product_title(brand, leaf, detail, applicable_pet_type),
                            "cover_image": cover,
                            "images": [
                                cover,
                                f"https://picsum.photos/seed/petmall-{leaf_count}-{variant}-detail/640/480",
                            ],
                            "price": price,
                            "original_price": original_price,
                            "stock": stock,
                            "status": "on_sale",
                            "description": (
                                f"分类路径：{top} / {second} / {leaf}。"
                                f"{detail}，适合作为商城测试、AI 导购检索和订单流程测试数据。"
                                f"价格、库存和规格为模拟数据，正式运营前请替换为真实商品信息。"
                            ),
                            "applicable_pet_type": applicable_pet_type,
                            "skus": skus,
                        }
                    )
    return products


def write_docs(products: list[dict]) -> None:
    leaf_names = {tuple(item["category_path"]) for item in products}
    by_top: dict[str, int] = {}
    for product in products:
        by_top[product["category_path"][0]] = by_top.get(product["category_path"][0], 0) + 1

    lines = [
        "# 商品分类对应种子商品数据说明",
        "",
        f"- 叶子分类数：{len(leaf_names)}",
        f"- 商品数：{len(products)}",
        f"- SKU 数：{sum(len(item['skus']) for item in products)}",
        "- 数据文件：`backend/scripts/data/category_products_seed.json`",
        "- 导入脚本：`backend/scripts/seed_products_from_categories.py`",
        "",
        "## 推荐使用方式",
        "",
        "商品脚本内部会自动补齐分类，所以通常只需要执行：",
        "",
        "```bash",
        "python backend/scripts/seed_products_from_categories.py",
        "```",
        "",
        "可先试运行，不落库：",
        "",
        "```bash",
        "python backend/scripts/seed_products_from_categories.py --dry-run",
        "```",
        "",
        "如需指定测试商家 ID：",
        "",
        "```bash",
        "python backend/scripts/seed_products_from_categories.py --merchant-id 3001",
        "```",
        "",
        "## 数据调整建议",
        "",
        "- `category` 必须对应 `seed_categories.py` 中的叶子分类名。",
        "- `price`、`original_price` 单位是分。",
        "- `applicable_pet_type` 可填 `dog`、`cat` 或 `null`。",
        "- `sku_code` 必须全局唯一；导入脚本用第一个 SKU 作为商品幂等识别键。",
        "- `cover_image` 当前使用 `picsum.photos` 测试图，正式数据建议替换为本地上传或对象存储 URL。",
        "",
        "## 顶层分类商品数量",
        "",
    ]
    for top, count in by_top.items():
        lines.append(f"- {top}：{count} 个商品")
    lines.extend(
        [
            "",
            "## 示例数据",
            "",
            "```json",
            json.dumps(products[:3], ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "商品分类商品种子数据说明.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    products = build_seed_products()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "category_products_seed.json").write_text(
        json.dumps(products, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_docs(products)
    print(f"Generated {len(products)} products for {len({tuple(item['category_path']) for item in products})} leaf categories.")


if __name__ == "__main__":
    main()
