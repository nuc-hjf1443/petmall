from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import not_found
from models.pet import PetDetailProfile, PetProfile
from repository.pet_repository import get_pet_detail_profile, get_user_pet
from repository.user_repository import get_user_by_id


DETAIL_FIELDS = (
    "body_size",
    "health_notes",
    "allergy_notes",
    "diet_preference",
    "product_preference",
    "behavior_notes",
    "care_notes",
)


def calculate_profile_completeness(pet: PetProfile, detail: PetDetailProfile | None) -> dict[str, Any]:
    values: dict[str, Any] = {
        "name": pet.name,
        "pet_type": pet.pet_type,
        "breed": pet.breed,
        "birthday": pet.birthday,
        "weight": pet.weight,
        "sterilized": pet.sterilized,
        "vaccine_status": pet.vaccine_status,
        "deworm_status": pet.deworm_status,
    }
    if detail is not None:
        values.update({field: getattr(detail, field) for field in DETAIL_FIELDS})
    else:
        values.update({field: None for field in DETAIL_FIELDS})
    total = len(values)
    missing = [field for field, value in values.items() if value is None or value == ""]
    completeness = round((total - len(missing)) * 100 / total)
    return {"pet_id": pet.id, "completeness": completeness, "missing_fields": missing}


def _text(value: Any) -> str:
    if value is None or value == "":
        return "未填写"
    return str(value)


def _snapshot(user, pet: PetProfile, detail: PetDetailProfile | None, completeness: dict[str, Any]) -> dict[str, Any]:
    profile = user.profile
    return {
        "user": {
            "id": user.id,
            "nickname": user.nickname,
            "city": user.city,
            "pet_experience": getattr(profile, "pet_experience", None),
            "living_city": getattr(profile, "living_city", None),
            "living_environment": getattr(profile, "living_environment", None),
            "budget_preference": getattr(profile, "budget_preference", None),
            "preferred_categories": getattr(profile, "preferred_categories", None),
            "feeding_philosophy": getattr(profile, "feeding_philosophy", None),
            "allergy_notes": getattr(profile, "allergy_notes", None),
        },
        "pet": {
            "id": pet.id,
            "name": pet.name,
            "pet_type": pet.pet_type,
            "breed": pet.breed,
            "gender": pet.gender,
            "birthday": pet.birthday.isoformat() if pet.birthday else None,
            "arrival_date": pet.arrival_date.isoformat() if pet.arrival_date else None,
            "weight": pet.weight,
            "sterilized": pet.sterilized,
            "vaccine_status": pet.vaccine_status,
            "deworm_status": pet.deworm_status,
        },
        "detail": {
            field: getattr(detail, field) if detail is not None else None
            for field in DETAIL_FIELDS
        },
        "profile_completeness": completeness,
    }


def _render_markdown(user, pet: PetProfile, detail: PetDetailProfile | None, completeness: dict[str, Any]) -> str:
    profile = user.profile
    recent_records = sorted(
        pet.growth_records,
        key=lambda item: item.happened_at or item.created_at,
        reverse=True,
    )[:10]
    reminders = sorted(pet.reminders, key=lambda item: item.due_at)[:10]
    lines = [
        "# 宠物资料文件",
        "",
        "## 用户养宠背景",
        f"- 昵称：{_text(user.nickname)}",
        f"- 所在城市：{_text(user.city or getattr(profile, 'living_city', None))}",
        f"- 养宠经验：{_text(getattr(profile, 'pet_experience', None))}",
        f"- 居住环境：{_text(getattr(profile, 'living_environment', None))}",
        f"- 预算偏好：{_text(getattr(profile, 'budget_preference', None))}",
        f"- 常购品类：{_text(getattr(profile, 'preferred_categories', None))}",
        f"- 喂养理念：{_text(getattr(profile, 'feeding_philosophy', None))}",
        f"- 用户过敏/禁忌备注：{_text(getattr(profile, 'allergy_notes', None))}",
        "",
        "## 宠物基础信息",
        f"- 昵称：{pet.name}",
        f"- 类型：{pet.pet_type}",
        f"- 品种：{_text(pet.breed)}",
        f"- 性别：{_text(pet.gender)}",
        f"- 生日：{_text(pet.birthday)}",
        f"- 到家日期：{_text(pet.arrival_date)}",
        f"- 当前体重：{_text(pet.weight)}",
        f"- 是否绝育：{_text(pet.sterilized)}",
        f"- 疫苗状态：{_text(pet.vaccine_status)}",
        f"- 驱虫状态：{_text(pet.deworm_status)}",
        "",
        "## 健康与护理记录",
        f"- 体型：{_text(getattr(detail, 'body_size', None))}",
        f"- 健康备注：{_text(getattr(detail, 'health_notes', None))}",
        f"- 过敏/禁忌：{_text(getattr(detail, 'allergy_notes', None))}",
        f"- 护理注意事项：{_text(getattr(detail, 'care_notes', None))}",
        "",
        "## 饮食与用品偏好",
        f"- 饮食偏好：{_text(getattr(detail, 'diet_preference', None))}",
        f"- 用品偏好：{_text(getattr(detail, 'product_preference', None))}",
        f"- 行为特点：{_text(getattr(detail, 'behavior_notes', None))}",
        "",
        "## 历史成长记录摘要",
    ]
    if recent_records:
        for record in recent_records:
            lines.append(
                f"- [{record.record_type}] {_text(record.title)}：{_text(record.content)}"
            )
    else:
        lines.append("- 暂无成长记录")
    lines.extend(["", "## 提醒与复购信息"])
    if reminders:
        for reminder in reminders:
            lines.append(
                f"- [{reminder.reminder_type}] {reminder.title}：{reminder.due_at.isoformat()}，状态 {reminder.status}"
            )
    else:
        lines.append("- 暂无提醒")
    lines.extend([
        "",
        "## 导购/问答注意事项",
        f"- 资料完整度：{completeness['completeness']}%",
        f"- 缺失字段：{', '.join(completeness['missing_fields']) or '无'}",
        "- 医疗、用药、急症问题仅可作为参考，需引导用户咨询兽医。",
    ])
    return "\n".join(lines)


async def get_pet_profile_completeness(db: AsyncSession, user_id: int, pet_id: int) -> dict[str, Any]:
    pet = await get_user_pet(db, user_id, pet_id)
    if pet is None:
        raise not_found("Pet not found")
    detail = await get_pet_detail_profile(db, user_id, pet_id)
    return calculate_profile_completeness(pet, detail)


async def get_pet_detail_summary(db: AsyncSession, user_id: int, pet_id: int) -> dict[str, Any]:
    pet = await get_user_pet(db, user_id, pet_id)
    if pet is None:
        raise not_found("Pet not found")
    detail = await get_pet_detail_profile(db, user_id, pet_id)
    completeness = calculate_profile_completeness(pet, detail)
    return {
        "pet_id": pet.id,
        "name": pet.name,
        "pet_type": pet.pet_type,
        "breed": pet.breed,
        "gender": pet.gender,
        "weight": pet.weight,
        "vaccine_status": pet.vaccine_status,
        "deworm_status": pet.deworm_status,
        "body_size": getattr(detail, "body_size", None),
        "health_notes": getattr(detail, "health_notes", None),
        "allergy_notes": getattr(detail, "allergy_notes", None),
        "diet_preference": getattr(detail, "diet_preference", None),
        "product_preference": getattr(detail, "product_preference", None),
        "behavior_notes": getattr(detail, "behavior_notes", None),
        "care_notes": getattr(detail, "care_notes", None),
        "profile_completeness": completeness,
    }


async def build_pet_profile_document(db: AsyncSession, user_id: int, pet_id: int) -> dict[str, Any]:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise not_found("User not found")
    pet = await get_user_pet(db, user_id, pet_id)
    if pet is None:
        raise not_found("Pet not found")
    detail = await get_pet_detail_profile(db, user_id, pet_id)
    completeness = calculate_profile_completeness(pet, detail)
    snapshot = _snapshot(user, pet, detail, completeness)
    content = _render_markdown(user, pet, detail, completeness)
    return {
        "pet_id": pet.id,
        "content": content,
        "source_snapshot": snapshot,
        "profile_completeness": completeness["completeness"],
        "missing_fields": completeness["missing_fields"],
    }


class RealPetProfileDocumentAdapter:
    async def generate(self, db: AsyncSession, user_id: int, pet_id: int):
        document = await build_pet_profile_document(db, user_id, pet_id)
        return document["source_snapshot"], document["content"]
