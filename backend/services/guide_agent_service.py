import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.agent_workflow import build_rule_based_guide_history_summary, run_guide_agent_workflow, summarize_guide_history
from core.errors import not_found
from core.rag_service import retrieve_private_knowledge
from models.agent import AgentMessage, AgentRecommendation, AgentSession
from models.user import User
from schemas.agent_schema import GuideSessionCreate
from services.product_service import get_product_for_agent, search_products_for_agent
from services.profile_document_service import get_pet_detail_summary


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


async def _build_guide_history_context(session: AgentSession) -> tuple[str, list[dict[str, str]]]:
    messages = sorted(session.messages, key=lambda item: item.id)
    old_messages = messages[:-GUIDE_RECENT_HISTORY_LIMIT]
    recent_messages = messages[-GUIDE_RECENT_HISTORY_LIMIT:]
    recent_history = _messages_to_history(recent_messages)
    if not old_messages:
        return session.context_summary or "", recent_history

    old_history = _messages_to_history(old_messages)
    try:
        summary = await summarize_guide_history(
            existing_summary=session.context_summary,
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
            session.context_summary,
            old_history,
            max_chars=GUIDE_HISTORY_SUMMARY_MAX_CHARS,
        )
    session.context_summary = summary
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
    try:
        products = await search_products_for_agent(db, query, pet_type, limit)
    except Exception as exc:
        logger.exception(
            "guide_agent_product_search_failed",
            extra={
                "stage": "product_search",
                "session_id": session_id,
                "user_id": user_id,
                "query": query,
                "pet_type": pet_type,
                "exception_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        return []
    if products:
        return products
    try:
        return await search_products_for_agent(db, "", pet_type, limit)
    except Exception as exc:
        logger.exception(
            "guide_agent_product_search_fallback_failed",
            extra={
                "stage": "product_search_fallback",
                "session_id": session_id,
                "user_id": user_id,
                "query": "",
                "pet_type": pet_type,
                "exception_type": type(exc).__name__,
                "error": str(exc),
            },
        )
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
) -> tuple[AgentMessage, AgentMessage, list[dict[str, Any]]]:
    session = await get_guide_session(db, user.id, session_id)
    risk_level = assess_guide_risk(content)
    pet_summary = None
    if session.pet_id is not None:
        pet_summary = await get_pet_detail_summary(db, user.id, session.pet_id)

    pet_type = pet_summary.get("pet_type") if pet_summary else None
    products = await _search_product_candidates(
        db,
        content,
        pet_type,
        limit,
        session_id=session_id,
        user_id=user.id,
    )
    rag_context, rag_references = await _retrieve_rag_context(db, user.id, session_id, content)
    history_summary, recent_history = await _build_guide_history_context(session)
    workflow_result = await run_guide_agent_workflow(
        question=content,
        risk_level=risk_level,
        pet_summary=pet_summary,
        products=products,
        rag_context=rag_context,
        history=recent_history,
        history_summary=history_summary,
        session_id=session_id,
    )
    picked = _pick_allowed_recommendations(
        workflow_result.get("recommendations", []),
        products,
        limit,
    )
    hydrated = await _hydrate_recommendations(db, picked, session_id=session_id, user_id=user.id)

    user_message = AgentMessage(
        session_id=session_id,
        role="user",
        content=content,
        risk_level=risk_level,
    )
    assistant_message = AgentMessage(
        session_id=session_id,
        role="assistant",
        content=workflow_result["answer"],
        risk_level=risk_level,
        references=rag_references or workflow_result.get("references"),
    )
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
    return user_message, assistant_message, hydrated
