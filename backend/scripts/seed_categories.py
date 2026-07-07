import asyncio
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.database import AsyncSessionLocal, engine
from models.product import ProductCategory


CATEGORY_TREE = (
    (
        "宠物食品",
        (
            ("主粮", ("狗粮", "猫粮", "幼犬粮", "成犬粮", "幼猫粮", "成猫粮", "老年粮")),
            ("零食", ("肉干", "冻干", "罐头", "猫条", "磨牙棒", "洁齿零食")),
            ("营养品", ("钙片", "鱼油", "卵磷脂", "益生菌", "维生素", "化毛膏")),
            ("处方特殊粮", ("肠胃调理粮", "泌尿护理粮", "减肥粮", "皮肤护理粮")),
        ),
    ),
    (
        "宠物用品",
        (
            ("日常用品", ("食盆", "水碗", "自动喂食器", "饮水机")),
            ("清洁用品", ("猫砂", "尿垫", "拾便袋", "除臭剂", "湿巾")),
            ("居家用品", ("宠物窝", "笼子", "围栏", "爬架", "垫子")),
            ("外出用品", ("牵引绳", "胸背带", "航空箱", "宠物包", "推车")),
            ("玩具用品", ("逗猫棒", "球类", "磨牙玩具", "益智玩具")),
        ),
    ),
    (
        "宠物洗护美容",
        (
            ("洗护用品", ("沐浴露", "护毛素", "干洗喷雾")),
            ("美容工具", ("梳子", "指甲剪", "剃毛器", "吹水机")),
            ("口腔护理", ("牙刷", "牙膏", "洁齿水")),
            ("耳眼护理", ("洗耳液", "眼部清洁湿巾", "泪痕清洁")),
        ),
    ),
    (
        "宠物健康医疗",
        (
            ("驱虫用品", ("体内驱虫", "体外驱虫", "内外同驱")),
            ("常用护理", ("皮肤喷剂", "伤口护理", "肠胃护理")),
            ("医疗辅助", ("伊丽莎白圈", "喂药器", "体温计")),
            ("疫苗体检服务", ("疫苗预约", "体检套餐", "线上问诊")),
        ),
    ),
    (
        "宠物服饰周边",
        (
            ("服装", ("春夏装", "秋冬装", "雨衣", "节日服")),
            ("配饰", ("项圈", "铃铛", "发夹", "围巾")),
            ("定制周边", ("宠物名牌", "照片定制", "纪念品")),
        ),
    ),
    (
        "宠物活体领养",
        (
            ("宠物出售", ("猫", "狗", "兔子", "仓鼠", "鸟类", "鱼类")),
            ("宠物领养", ("免费领养", "公益领养", "救助领养")),
            ("商家宠物", ("猫舍", "犬舍", "认证商家")),
            ("领养资料", ("疫苗情况", "驱虫情况", "健康证明", "血统证明")),
        ),
    ),
    (
        "宠物服务",
        (
            ("洗护美容", ("洗澡", "美容", "剪毛", "修甲")),
            ("寄养托管", ("日托", "短期寄养", "长期寄养")),
            ("医疗服务", ("体检", "疫苗", "绝育", "问诊")),
            ("训练服务", ("行为纠正", "定点排便", "服从训练")),
            ("上门服务", ("上门喂养", "上门遛狗", "上门洗护")),
        ),
    ),
)


async def seed_categories(db: AsyncSession) -> tuple[int, int]:
    result = await db.execute(select(ProductCategory))
    categories_by_name = {category.name: category for category in result.scalars().all()}
    created = 0
    updated = 0

    async def upsert_category(
        name: str,
        parent_id: int | None,
        sort_order: int,
    ) -> ProductCategory:
        nonlocal created, updated

        category = categories_by_name.get(name)
        if category is None:
            category = ProductCategory(
                parent_id=parent_id,
                name=name,
                sort_order=sort_order,
                is_enabled=True,
            )
            db.add(category)
            await db.flush()
            categories_by_name[name] = category
            created += 1
            return category

        changed = False
        if category.parent_id != parent_id:
            category.parent_id = parent_id
            changed = True
        if category.sort_order != sort_order:
            category.sort_order = sort_order
            changed = True
        if not category.is_enabled:
            category.is_enabled = True
            changed = True
        updated += int(changed)
        return category

    for top_index, (top_name, second_level_categories) in enumerate(CATEGORY_TREE, start=1):
        top_category = await upsert_category(top_name, None, top_index * 10000)
        for second_index, (second_name, third_level_names) in enumerate(
            second_level_categories,
            start=1,
        ):
            second_category = await upsert_category(
                second_name,
                top_category.id,
                top_index * 10000 + second_index * 100,
            )
            for third_index, third_name in enumerate(third_level_names, start=1):
                await upsert_category(
                    third_name,
                    second_category.id,
                    top_index * 10000 + second_index * 100 + third_index,
                )

    await db.commit()
    return created, updated


async def main() -> None:
    try:
        async with AsyncSessionLocal() as db:
            created, updated = await seed_categories(db)
        print(f"Seeded product categories: created={created}, updated={updated}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
