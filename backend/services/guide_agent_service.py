import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.agent_workflow import run_guide_agent_workflow
from core.errors import not_found
from core.rag_service import retrieve_private_knowledge
from models.agent import AgentMessage, AgentRecommendation, AgentSession
from models.user import User
from schemas.agent_schema import GuideSessionCreate
from services.product_service import get_product_for_agent, search_products_for_agent
from services.profile_document_service import get_pet_detail_summary


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


async def _search_product_candidates(
    db: AsyncSession,
    query: str,
    pet_type: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    products = await search_products_for_agent(db, query, pet_type, limit)
    if products or not pet_type:
        return products
    return await search_products_for_agent(db, "", pet_type, limit)


async def _retrieve_rag_context(db: AsyncSession, user_id: int, query: str) -> tuple[str, str | None]:
    try:
        private_results = await retrieve_private_knowledge(db, user_id, query, top_k=3, caller="guide_agent")
    except Exception:
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
        product_id = int(item.get("product_id") or 0)
        if product_id not in products_by_id or product_id in seen_product_ids:
            continue
        product = products_by_id[product_id]
        sku_id = item.get("sku_id")
        allowed_sku_ids = {
            int(sku["id"])
            for sku in product.get("skus") or []
            if sku.get("is_enabled", True) and int(sku.get("stock") or 0) > 0
        }
        if sku_id is not None and int(sku_id) not in allowed_sku_ids:
            sku_id = None
        if sku_id is None and allowed_sku_ids:
            sku_id = sorted(allowed_sku_ids)[0]
        picked.append(
            {
                "product_id": product_id,
                "sku_id": int(sku_id) if sku_id is not None else None,
                "rank": len(picked) + 1,
                "reason": str(item.get("reason") or "Matched the user's shopping request."),
                "caution": item.get("caution"),
                "source": str(item.get("source") or "product_search"),
            }
        )
        seen_product_ids.add(product_id)
        if len(picked) >= limit:
            break
    return picked


async def _hydrate_recommendations(
    db: AsyncSession,
    recommendations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hydrated: list[dict[str, Any]] = []
    for item in recommendations:
        try:
            product = await get_product_for_agent(db, item["product_id"])
        except Exception:
            continue
        hydrated.append({**item, "product": product})
    return hydrated


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
    products = await _search_product_candidates(db, content, pet_type, limit)
    rag_context, rag_references = await _retrieve_rag_context(db, user.id, content)
    workflow_result = await run_guide_agent_workflow(
        question=content,
        risk_level=risk_level,
        pet_summary=pet_summary,
        products=products,
        rag_context=rag_context,
        history=_messages_to_history(session.messages),
        session_id=session_id,
    )
    picked = _pick_allowed_recommendations(
        workflow_result.get("recommendations", []),
        products,
        limit,
    )
    hydrated = await _hydrate_recommendations(db, picked)

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
            )
        )

    await db.commit()
    await db.refresh(user_message)
    await db.refresh(assistant_message)
    return user_message, assistant_message, hydrated
