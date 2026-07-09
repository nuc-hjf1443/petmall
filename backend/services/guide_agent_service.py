import json
import logging
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.agent_workflow import (
    build_rule_based_guide_answer,
    build_rule_based_guide_history_summary,
    run_guide_agent_workflow,
    summarize_guide_history,
)
from core.errors import not_found
from core.rag_service import retrieve_private_knowledge
from models.agent import AgentMessage, AgentRecommendation, AgentSession
from models.user import User
from schemas.agent_schema import GuideSessionCreate
from services.product_service import get_product_for_agent, search_products_for_agent
from services.profile_document_service import get_pet_detail_summary
from services.pet_service import list_pets


logger = logging.getLogger(__name__)
GUIDE_RECENT_HISTORY_LIMIT = 8
GUIDE_HISTORY_SUMMARY_MAX_CHARS = 1200

HIGH_RISK_KEYWORDS = (
    "\u4e2d\u6bd2",
    "\u547c\u5438\u56f0\u96be",
    "\u4f11\u514b",
    "\u660f\u8ff7",
    "\u62bd\u6410",
    "\u6025\u75c7",
    "emergency",
    "poison",
)
MEDICAL_KEYWORDS = (
    "\u7528\u836f",
    "\u836f\u91cf",
    "\u5242\u91cf",
    "\u5904\u65b9",
    "\u6297\u751f\u7d20",
    "\u5904\u65b9\u7cae",
    "\u5455\u5410",
    "\u4fbf\u8840",
    "\u53d1\u70e7",
    "\u611f\u67d3",
    "\u75ab\u82d7",
    "\u9a71\u866b",
    "medicine",
    "dosage",
    "prescription",
)

DOG_QUERY_KEYWORDS = (
    "\u67ef\u57fa",
    "\u91d1\u6bdb",
    "\u62c9\u5e03\u62c9\u591a",
    "\u6cf0\u8fea",
    "\u67f4\u72ac",
    "\u6bd4\u718a",
    "\u8fb9\u7267",
    "\u72d7",
    "\u72ac",
    "\u72d7\u7cae",
    "\u72ac\u7cae",
    "dog",
    "puppy",
)
CAT_QUERY_KEYWORDS = (
    "\u5e03\u5076",
    "\u82f1\u77ed",
    "\u7f05\u56e0",
    "\u6a58\u732b",
    "\u5e7c\u732b",
    "\u732b",
    "\u732b\u7cae",
    "\u732b\u7802",
    "cat",
    "kitten",
)

DOG_PRODUCT_SEARCH_TERMS = ("\u72d7\u7cae", "\u72ac\u7cae", "\u4f4e\u654f", "\u72d7", "\u72ac")
CAT_PRODUCT_SEARCH_TERMS = ("\u732b\u7cae", "\u732b\u7802", "\u4f4e\u654f", "\u732b", "\u5e7c\u732b")
PRODUCT_INTENT_TERMS = (
    "\u51bb\u5e72",
    "\u96f6\u98df",
    "\u4e3b\u7cae",
    "\u72d7\u7cae",
    "\u732b\u7cae",
    "\u73a9\u5177",
    "\u6d17\u62a4",
    "\u6d74\u9732",
    "\u7259\u5237",
    "\u7259\u818f",
    "\u732b\u7802",
    "\u7275\u5f15",
    "\u8425\u517b",
)
GUIDE_STATE_VERSION = 1
RAW_PRODUCT_FIELD_PATTERN = re.compile(
    r"\b(product_id|sku_id|price|stock)\s*=|product_id|sku_id|价格\s*\d|库存\s*\d",
    re.IGNORECASE,
)


async def create_guide_session(
    db: AsyncSession,
    user: User,
    payload: GuideSessionCreate,
) -> AgentSession:
    if payload.pet_id is not None:
        await get_pet_detail_summary(db, user.id, payload.pet_id)
    session = AgentSession(
        user_id=user.id,
        agent_type="guide",
        title=payload.title,
        pet_id=payload.pet_id,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_guide_session(db: AsyncSession, user_id: int, session_id: int) -> AgentSession:
    result = await db.execute(
        select(AgentSession)
        .options(selectinload(AgentSession.messages))
        .where(
            AgentSession.id == session_id,
            AgentSession.user_id == user_id,
            AgentSession.agent_type == "guide",
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise not_found("Agent session not found")
    return session


def assess_guide_risk(content: str) -> str:
    text = content.lower()
    if any(keyword in text for keyword in HIGH_RISK_KEYWORDS):
        return "high"
    if any(keyword in text for keyword in MEDICAL_KEYWORDS):
        return "medical"
    return "normal"


def _empty_guide_state() -> dict[str, Any]:
    return {
        "version": GUIDE_STATE_VERSION,
        "stage": "collecting",
        "slots": {},
        "missing_slots": [],
        "history_summary": "",
    }


def _load_guide_state(session: AgentSession) -> dict[str, Any]:
    if not session.context_summary:
        return _empty_guide_state()
    try:
        parsed = json.loads(session.context_summary)
    except json.JSONDecodeError:
        state = _empty_guide_state()
        state["history_summary"] = session.context_summary
        return state
    if not isinstance(parsed, dict):
        return _empty_guide_state()
    state = _empty_guide_state()
    state.update(parsed)
    if not isinstance(state.get("slots"), dict):
        state["slots"] = {}
    if not isinstance(state.get("missing_slots"), list):
        state["missing_slots"] = []
    return state


def _save_guide_state(session: AgentSession, guide_state: dict[str, Any]) -> None:
    state = _empty_guide_state()
    state.update(guide_state or {})
    state["version"] = GUIDE_STATE_VERSION
    session.context_summary = json.dumps(state, ensure_ascii=False)


def _guide_slots(guide_state: dict[str, Any]) -> dict[str, Any]:
    slots = guide_state.get("slots")
    if not isinstance(slots, dict):
        slots = {}
        guide_state["slots"] = slots
    return slots


def _extract_budget(content: str) -> int | None:
    match = re.search(r"(\d{2,6})\s*(?:\u5143|\u5757|rmb|RMB)?", content or "")
    if match:
        return int(match.group(1))
    chinese_budget_map = {
        "\u4e00\u767e": 100,
        "\u4e24\u767e": 200,
        "\u4e8c\u767e": 200,
        "\u4e09\u767e": 300,
        "\u4e94\u767e": 500,
    }
    for keyword, value in chinese_budget_map.items():
        if keyword in content:
            return value
    return None


def _extract_category(content: str) -> str | None:
    category_keywords = {
        "freeze_dried": ("\u51bb\u5e72",),
        "snack": ("\u96f6\u98df", "\u7f50\u5934", "\u5999\u9c9c\u5305"),
        "food": ("\u4e3b\u7cae", "\u72d7\u7cae", "\u732b\u7cae", "food"),
        "toy": ("\u73a9\u5177", "\u7403", "\u8010\u54ac", "toy"),
        "bath": ("\u6d17\u62a4", "\u6d74\u9732", "\u6d17\u6fa1"),
        "litter": ("\u732b\u7802",),
        "leash": ("\u7275\u5f15", "\u9879\u5708"),
    }
    lowered = (content or "").lower()
    for category, keywords in category_keywords.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return category
    return None


def _extract_preferences(content: str) -> list[str]:
    preference_keywords = (
        "\u4f4e\u654f",
        "\u65e0\u8c37",
        "\u9ad8\u86cb\u767d",
        "\u8010\u54ac",
        "\u53bb\u6cea\u75d5",
        "\u4fbf\u643a",
        "\u9e21\u8089",
        "\u725b\u8089",
        "\u9c7c",
        "sensitive",
        "allergy",
    )
    lowered = (content or "").lower()
    return [keyword for keyword in preference_keywords if keyword.lower() in lowered][:5]


def _merge_guide_state_from_content(guide_state: dict[str, Any], content: str) -> None:
    slots = _guide_slots(guide_state)
    if pet_type := infer_pet_type_from_guide_query(content):
        slots["pet_type"] = pet_type
    if budget := _extract_budget(content):
        slots["budget"] = budget
    if category := _extract_category(content):
        slots["category"] = category
    preferences = _extract_preferences(content)
    if preferences:
        existing = [str(item) for item in slots.get("preferences") or [] if str(item).strip()]
        for preference in preferences:
            if preference not in existing:
                existing.append(preference)
        slots["preferences"] = existing


def _missing_guide_slots(guide_state: dict[str, Any]) -> list[str]:
    slots = _guide_slots(guide_state)
    missing: list[str] = []
    if not slots.get("pet_id") and not slots.get("pet_type"):
        missing.append("pet")
    if not slots.get("category"):
        missing.append("category")
    if (
        not slots.get("budget")
        and not slots.get("preferences")
        and not (slots.get("category") and (slots.get("pet_id") or slots.get("pet_type")))
    ):
        missing.append("budget_or_preference")
    return missing


def infer_pet_type_from_guide_query(content: str) -> str | None:
    text = (content or "").lower()
    dog_score = sum(1 for keyword in DOG_QUERY_KEYWORDS if keyword.lower() in text)
    cat_score = sum(1 for keyword in CAT_QUERY_KEYWORDS if keyword.lower() in text)
    if re.search(r"\bdog\b|\bpuppy\b", text):
        dog_score += 2
    if re.search(r"\bcat\b|\bkitten\b", text):
        cat_score += 2
    if dog_score > cat_score:
        return "dog"
    if cat_score > dog_score:
        return "cat"
    return None


def _product_matches_pet_type(product: dict[str, Any], pet_type: str | None) -> bool:
    if not pet_type:
        return True
    product_pet_type = str(product.get("applicable_pet_type") or "").strip()
    return not product_pet_type or product_pet_type == pet_type


def _filter_products_by_pet_type(products: list[dict[str, Any]], pet_type: str | None) -> list[dict[str, Any]]:
    return [product for product in products if _product_matches_pet_type(product, pet_type)]


def _guide_product_search_queries(query: str, pet_type: str | None) -> list[str]:
    queries: list[str] = []
    if query.strip():
        queries.append(query.strip())
    keywords = DOG_PRODUCT_SEARCH_TERMS if pet_type == "dog" else CAT_PRODUCT_SEARCH_TERMS if pet_type == "cat" else ()
    text = query.lower()
    for keyword in PRODUCT_INTENT_TERMS:
        if keyword.lower() in text and keyword not in queries:
            queries.append(keyword)
    for keyword in keywords:
        if keyword.lower() in text and keyword not in queries:
            queries.append(keyword)
    return queries or [""]


def _messages_to_history(messages: list[AgentMessage]) -> list[dict[str, str]]:
    return [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in sorted(messages, key=lambda item: item.id)
    ]


def _json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    return []


def _json_dumps_list(value: Any) -> str | None:
    items = _json_list(value)
    if not items:
        return None
    return json.dumps(items, ensure_ascii=False)


def _safe_score(value: Any) -> float | None:
    if value is None:
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(score, 1.0))


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _answer_contains_raw_product_fields(answer: str) -> bool:
    return bool(RAW_PRODUCT_FIELD_PATTERN.search(answer or ""))


def _normalize_guide_answer_for_cards(
    answer: str | None,
    *,
    risk_level: str,
    products: list[dict[str, Any]],
    pet_summary: dict[str, Any] | None,
) -> str:
    text = str(answer or "").strip()
    if not text or _answer_contains_raw_product_fields(text):
        return build_rule_based_guide_answer(risk_level, products, pet_summary)
    return text


async def _build_guide_history_context(
    session: AgentSession,
    guide_state: dict[str, Any],
) -> tuple[str, list[dict[str, str]]]:
    messages = sorted(session.messages, key=lambda item: item.id)
    old_messages = messages[:-GUIDE_RECENT_HISTORY_LIMIT]
    recent_messages = messages[-GUIDE_RECENT_HISTORY_LIMIT:]
    recent_history = _messages_to_history(recent_messages)
    existing_summary = str(guide_state.get("history_summary") or "")
    if not old_messages:
        return existing_summary, recent_history

    old_history = _messages_to_history(old_messages)
    try:
        summary = await summarize_guide_history(
            existing_summary=existing_summary,
            history=old_history,
            max_chars=GUIDE_HISTORY_SUMMARY_MAX_CHARS,
        )
    except Exception as exc:
        logger.exception(
            "guide_agent_history_summary_failed",
            extra={
                "stage": "history_summary",
                "session_id": session.id,
                "user_id": session.user_id,
                "exception_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        summary = build_rule_based_guide_history_summary(
            existing_summary,
            old_history,
            max_chars=GUIDE_HISTORY_SUMMARY_MAX_CHARS,
        )
    guide_state["history_summary"] = summary
    return summary, recent_history


async def _search_product_candidates(
    db: AsyncSession,
    query: str,
    pet_type: str | None,
    limit: int,
    *,
    session_id: int,
    user_id: int,
) -> list[dict[str, Any]]:
    for search_query in _guide_product_search_queries(query, pet_type):
        try:
            products = await search_products_for_agent(db, search_query, pet_type, limit)
        except Exception as exc:
            logger.exception(
                "guide_agent_product_search_failed",
                extra={
                    "stage": "product_search",
                    "session_id": session_id,
                    "user_id": user_id,
                    "query": search_query,
                    "pet_type": pet_type,
                    "exception_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            return []
        products = _filter_products_by_pet_type(products, pet_type)
        if products:
            return products
    return []


async def _retrieve_rag_context(db: AsyncSession, user_id: int, session_id: int, query: str) -> tuple[str, str | None]:
    try:
        private_results = await retrieve_private_knowledge(db, user_id, query, top_k=3, caller="guide_agent")
    except Exception as exc:
        logger.exception(
            "guide_agent_rag_failed",
            extra={
                "stage": "rag",
                "session_id": session_id,
                "user_id": user_id,
                "query": query,
                "exception_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        private_results = []
    if not private_results:
        return "", None

    lines = []
    references = []
    for index, item in enumerate(private_results, start=1):
        content = str(item.get("content", "")).strip()
        metadata = item.get("metadata") or {}
        score = item.get("score")
        if not content:
            continue
        lines.append(f"[{index}] {content[:800]}")
        references.append(
            {
                "scope": "private",
                "document_id": metadata.get("document_id"),
                "score": score,
            }
        )
    if not lines:
        return "", None
    return "\n".join(lines), json.dumps(references, ensure_ascii=False)


async def _resolve_guide_pet_summary(
    db: AsyncSession,
    user: User,
    session: AgentSession,
    guide_state: dict[str, Any],
    content: str,
) -> dict[str, Any] | None:
    slots = _guide_slots(guide_state)
    pet_id = session.pet_id or _safe_int(slots.get("pet_id"))
    if pet_id is None:
        pets = await list_pets(db, user.id)
        for pet in pets:
            pet_name = str(getattr(pet, "name", "") or "").strip()
            if pet_name and pet_name in content:
                pet_id = pet.id
                session.pet_id = pet.id
                slots["pet_id"] = pet.id
                slots["pet_name"] = pet.name
                slots["pet_type"] = pet.pet_type
                break
    if pet_id is None:
        return None
    pet_summary = await get_pet_detail_summary(db, user.id, pet_id)
    slots["pet_id"] = pet_id
    if pet_summary.get("name"):
        slots["pet_name"] = pet_summary.get("name")
    if pet_summary.get("pet_type"):
        slots["pet_type"] = pet_summary.get("pet_type")
    return pet_summary


def _pick_allowed_recommendations(
    raw_recommendations: list[dict[str, Any]],
    products: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    products_by_id = {int(product["id"]): product for product in products}
    picked: list[dict[str, Any]] = []
    seen_product_ids: set[int] = set()
    for item in raw_recommendations:
        product_id = _safe_int(item.get("product_id"))
        if product_id is None:
            continue
        if product_id not in products_by_id or product_id in seen_product_ids:
            continue
        product = products_by_id[product_id]
        sku_id = _safe_int(item.get("sku_id"))
        allowed_sku_ids = {
            int(sku["id"])
            for sku in product.get("skus") or []
            if sku.get("is_enabled", True) and int(sku.get("stock") or 0) > 0
        }
        if sku_id is not None and sku_id not in allowed_sku_ids:
            sku_id = None
        if sku_id is None and allowed_sku_ids:
            sku_id = sorted(allowed_sku_ids)[0]
        source = str(item.get("source") or "product_search")
        picked.append(
            {
                "product_id": product_id,
                "sku_id": sku_id,
                "rank": len(picked) + 1,
                "reason": str(item.get("reason") or "Matched the user's shopping request."),
                "caution": item.get("caution"),
                "source": source,
                "source_detail": item.get("source_detail") or ("rag_enhanced" if source == "rag_enhanced" else "llm_selected"),
                "score": _safe_score(item.get("score")),
                "matched_pet_fields": _json_list(item.get("matched_pet_fields")),
            }
        )
        seen_product_ids.add(product_id)
        if len(picked) >= limit:
            break
    return picked


async def _hydrate_recommendations(
    db: AsyncSession,
    recommendations: list[dict[str, Any]],
    *,
    session_id: int,
    user_id: int,
) -> list[dict[str, Any]]:
    hydrated: list[dict[str, Any]] = []
    for item in recommendations:
        try:
            product = await get_product_for_agent(db, item["product_id"])
        except Exception as exc:
            logger.exception(
                "guide_agent_recommendation_hydration_failed",
                extra={
                    "stage": "recommendation_hydration",
                    "session_id": session_id,
                    "user_id": user_id,
                    "product_id": item.get("product_id"),
                    "exception_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            continue
        hydrated.append({**item, "product": product})
    return hydrated


async def list_latest_guide_recommendations(
    db: AsyncSession,
    user: User,
    session_id: int,
) -> list[dict[str, Any]]:
    await get_guide_session(db, user.id, session_id)
    latest_message_id = await db.scalar(
        select(AgentMessage.id)
        .where(
            AgentMessage.session_id == session_id,
            AgentMessage.role == "assistant",
        )
        .order_by(AgentMessage.id.desc())
        .limit(1)
    )
    if latest_message_id is None:
        return []

    result = await db.execute(
        select(AgentRecommendation)
        .where(
            AgentRecommendation.session_id == session_id,
            AgentRecommendation.message_id == latest_message_id,
            AgentRecommendation.user_id == user.id,
        )
        .order_by(AgentRecommendation.rank, AgentRecommendation.id)
    )
    recommendations = [
        {
            "product_id": item.product_id,
            "sku_id": item.sku_id,
            "rank": item.rank,
            "reason": item.reason,
            "caution": item.caution,
            "source": item.source,
            "source_detail": item.source_detail,
            "score": item.score,
            "matched_pet_fields": _json_list(item.matched_pet_fields),
        }
        for item in result.scalars().all()
    ]
    return await _hydrate_recommendations(db, recommendations, session_id=session_id, user_id=user.id)


async def send_guide_message(
    db: AsyncSession,
    user: User,
    session_id: int,
    content: str,
    limit: int,
) -> tuple[AgentMessage, AgentMessage, list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], bool]:
    session = await get_guide_session(db, user.id, session_id)
    risk_level = assess_guide_risk(content)
    guide_state = _load_guide_state(session)
    _merge_guide_state_from_content(guide_state, content)
    pet_summary = await _resolve_guide_pet_summary(db, user, session, guide_state, content)

    missing_slots = _missing_guide_slots(guide_state)
    guide_state["missing_slots"] = missing_slots
    guide_state["stage"] = "clarifying" if missing_slots else "searching"

    products: list[dict[str, Any]] = []
    rag_context = ""
    rag_references = None
    if not missing_slots:
        slots = _guide_slots(guide_state)
        requested_pet_type = infer_pet_type_from_guide_query(content)
        pet_type = requested_pet_type or slots.get("pet_type") or (pet_summary.get("pet_type") if pet_summary else None)
        products = await _search_product_candidates(
            db,
            content,
            pet_type,
            limit,
            session_id=session_id,
            user_id=user.id,
        )
        rag_context, rag_references = await _retrieve_rag_context(db, user.id, session_id, content)

    history_summary, recent_history = await _build_guide_history_context(session, guide_state)
    workflow_result = await run_guide_agent_workflow(
        question=content,
        risk_level=risk_level,
        pet_summary=pet_summary,
        products=products,
        rag_context=rag_context,
        history=recent_history,
        history_summary=history_summary,
        guide_state=guide_state,
        session_id=session_id,
    )
    guide_state = workflow_result.get("guide_state") or guide_state
    next_questions = workflow_result.get("next_questions", [])
    requires_user_confirmation = bool(workflow_result.get("requires_user_confirmation"))
    picked = _pick_allowed_recommendations(
        [] if requires_user_confirmation else workflow_result.get("recommendations", []),
        products,
        limit,
    )
    hydrated = await _hydrate_recommendations(db, picked, session_id=session_id, user_id=user.id)
    if not requires_user_confirmation and workflow_result.get("recommendations") and not hydrated:
        assistant_answer = build_rule_based_guide_answer(risk_level, [], pet_summary)
    else:
        assistant_answer = _normalize_guide_answer_for_cards(
            workflow_result.get("answer"),
            risk_level=risk_level,
            products=products,
            pet_summary=pet_summary,
        )

    user_message = AgentMessage(
        session_id=session_id,
        role="user",
        content=content,
        risk_level=risk_level,
    )
    assistant_message = AgentMessage(
        session_id=session_id,
        role="assistant",
        content=assistant_answer,
        risk_level=risk_level,
        references=rag_references or workflow_result.get("references"),
    )
    _save_guide_state(session, guide_state)
    db.add_all([user_message, assistant_message])
    await db.flush()

    for item in hydrated:
        db.add(
            AgentRecommendation(
                session_id=session_id,
                message_id=assistant_message.id,
                user_id=user.id,
                product_id=item["product_id"],
                sku_id=item.get("sku_id"),
                rank=item["rank"],
                reason=item["reason"],
                caution=item.get("caution"),
                source=item.get("source") or "product_search",
                source_detail=item.get("source_detail"),
                score=item.get("score"),
                matched_pet_fields=_json_dumps_list(item.get("matched_pet_fields")),
            )
        )

    await db.commit()
    await db.refresh(user_message)
    await db.refresh(assistant_message)
    return user_message, assistant_message, hydrated, guide_state, next_questions, requires_user_confirmation
