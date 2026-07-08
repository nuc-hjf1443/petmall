import json

from sqlalchemy import func, select
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.rag_service import retrieve_platform_knowledge, retrieve_private_knowledge
from core.agent_workflow import run_qa_agent_workflow
from core.errors import not_found
from models.agent import AgentMessage, AgentSession
from models.base import utc_now
from models.user import User
from schemas.agent_schema import QaSessionCreate


HIGH_RISK_KEYWORDS = (
    "抽搐",
    "呼吸困难",
    "中毒",
    "吐血",
    "便血",
    "昏迷",
    "休克",
    "急症",
    "emergency",
    "poison",
)
MEDICAL_KEYWORDS = (
    "用药",
    "药量",
    "剂量",
    "处方",
    "抗生素",
    "拉稀",
    "呕吐",
    "发烧",
    "感染",
    "疫苗",
    "驱虫",
    "病",
)


async def create_qa_session(db: AsyncSession, user: User, payload: QaSessionCreate) -> AgentSession:
    session = AgentSession(
        user_id=user.id,
        agent_type="qa",
        title=payload.title,
        pet_id=payload.pet_id,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_user_session(
    db: AsyncSession,
    user_id: int,
    session_id: int,
    agent_type: str | None = "qa",
) -> AgentSession:
    filters = [
        AgentSession.id == session_id,
        AgentSession.user_id == user_id,
    ]
    if agent_type is not None:
        filters.append(AgentSession.agent_type == agent_type)
    result = await db.execute(
        select(AgentSession)
        .options(
            selectinload(AgentSession.messages),
            selectinload(AgentSession.recommendations),
        )
        .where(*filters)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise not_found("Agent session not found")
    return session


async def list_user_sessions(
    db: AsyncSession,
    user_id: int,
    *,
    agent_type: str | None,
    page: int,
    page_size: int,
) -> dict:
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 50)
    filters = [AgentSession.user_id == user_id]
    if agent_type is not None:
        filters.append(AgentSession.agent_type == agent_type)

    total = int((await db.scalar(select(func.count(AgentSession.id)).where(*filters))) or 0)
    latest_message = (
        select(
            AgentMessage.session_id,
            func.max(AgentMessage.created_at).label("latest_message_at"),
        )
        .group_by(AgentMessage.session_id)
        .subquery()
    )
    result = await db.execute(
        select(AgentSession)
        .outerjoin(latest_message, latest_message.c.session_id == AgentSession.id)
        .options(selectinload(AgentSession.messages))
        .where(*filters)
        .order_by(func.coalesce(latest_message.c.latest_message_at, AgentSession.updated_at).desc(), AgentSession.id.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
    )
    sessions = list(result.scalars().unique().all())
    items = []
    for session in sessions:
        messages = sorted(session.messages, key=lambda item: item.id)
        latest_message = messages[-1] if messages else None
        items.append(
            {
                "id": session.id,
                "agent_type": session.agent_type,
                "title": session.title,
                "pet_id": session.pet_id,
                "latest_message_content": latest_message.content if latest_message else None,
                "latest_message_at": latest_message.created_at if latest_message else None,
                "message_count": len(messages),
                "created_at": session.created_at,
                "updated_at": session.updated_at,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }


async def list_qa_sessions(db: AsyncSession, user_id: int) -> list[dict]:
    result = await db.execute(
        select(AgentSession)
        .options(selectinload(AgentSession.messages))
        .where(
            AgentSession.user_id == user_id,
            AgentSession.agent_type == "qa",
        )
        .order_by(desc(AgentSession.updated_at), desc(AgentSession.id))
    )
    sessions = result.scalars().all()
    items = []
    for session in sessions:
        messages = sorted(session.messages, key=lambda item: item.id)
        last_message = messages[-1] if messages else None
        items.append(
            {
                "id": session.id,
                "agent_type": session.agent_type,
                "title": session.title,
                "pet_id": session.pet_id,
                "last_message": last_message.content[:80] if last_message else None,
                "last_role": last_message.role if last_message else None,
                "message_count": len(messages),
                "is_pending": bool(last_message and last_message.role == "user"),
                "created_at": session.created_at,
                "updated_at": session.updated_at,
            }
        )
    return items


async def delete_qa_session(db: AsyncSession, user_id: int, session_id: int) -> None:
    session = await get_user_session(db, user_id, session_id, agent_type="qa")
    await db.delete(session)
    await db.commit()


async def delete_user_session(
    db: AsyncSession,
    user_id: int,
    session_id: int,
    agent_type: str | None = None,
) -> None:
    session = await get_user_session(db, user_id, session_id, agent_type=agent_type)
    await db.delete(session)
    await db.commit()


def assess_risk(content: str) -> str:
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


async def _retrieve_rag_context(db: AsyncSession, user_id: int, query: str) -> tuple[str, str | None]:
    try:
        private_results = await retrieve_private_knowledge(db, user_id, query, top_k=3, caller="qa_agent")
    except Exception:
        private_results = []
    try:
        platform_results = await retrieve_platform_knowledge(db, query, top_k=3, caller="qa_agent")
    except Exception:
        platform_results = []

    combined = [
        {"scope": "private", **item}
        for item in private_results
    ] + [
        {"scope": "platform", **item}
        for item in platform_results
    ]
    if not combined:
        return "", None

    lines = []
    references = []
    for index, item in enumerate(combined, start=1):
        content = str(item.get("content", "")).strip()
        metadata = item.get("metadata") or {}
        score = item.get("score")
        if not content:
            continue
        lines.append(f"[{index}] {content[:800]}")
        references.append(
            {
                "scope": item.get("scope"),
                "document_id": metadata.get("document_id"),
                "score": score,
            }
        )
    return "\n".join(lines), json.dumps(references, ensure_ascii=False)


async def send_qa_message(
    db: AsyncSession,
    user: User,
    session_id: int,
    content: str,
) -> tuple[AgentMessage, AgentMessage]:
    session = await get_user_session(db, user.id, session_id)
    risk_level = assess_risk(content)
    history = _messages_to_history(session.messages)
    user_message = AgentMessage(
        session_id=session_id,
        role="user",
        content=content,
        risk_level=risk_level,
    )
    if not session.title:
        session.title = content[:48]
    session.updated_at = utc_now()
    db.add(user_message)
    await db.commit()
    await db.refresh(user_message)

    rag_context, rag_references = await _retrieve_rag_context(db, user.id, content)
    workflow_result = await run_qa_agent_workflow(
        question=content,
        risk_level=risk_level,
        history=history,
        rag_context=rag_context,
        session_id=session_id,
    )
    assistant_message = AgentMessage(
        session_id=session_id,
        role="assistant",
        content=workflow_result["answer"],
        risk_level=risk_level,
        references=rag_references or workflow_result.get("references"),
    )
    session.updated_at = utc_now()
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)
    return user_message, assistant_message


async def queue_qa_message(
    db: AsyncSession,
    user: User,
    session_id: int,
    content: str,
) -> AgentMessage:
    session = await get_user_session(db, user.id, session_id)
    risk_level = assess_risk(content)
    user_message = AgentMessage(
        session_id=session_id,
        role="user",
        content=content,
        risk_level=risk_level,
    )
    if not session.title:
        session.title = content[:48]
    session.updated_at = utc_now()
    db.add(user_message)
    await db.commit()
    await db.refresh(user_message)
    return user_message


async def complete_qa_message(db: AsyncSession, user_id: int, session_id: int, content: str) -> None:
    try:
        session = await get_user_session(db, user_id, session_id)
    except Exception:
        return
    risk_level = assess_risk(content)
    sorted_messages = sorted(session.messages, key=lambda item: item.id)
    history = _messages_to_history(sorted_messages[:-1])
    try:
        rag_context, rag_references = await _retrieve_rag_context(db, user_id, content)
        workflow_result = await run_qa_agent_workflow(
            question=content,
            risk_level=risk_level,
            history=history,
            rag_context=rag_context,
            session_id=session_id,
        )
        content_text = workflow_result["answer"]
        references = rag_references or workflow_result.get("references")
    except Exception:
        content_text = "暂时无法完成回答。你可以稍后重新进入会话查看，或换一种描述再试一次。"
        references = None

    session.updated_at = utc_now()
    db.add(
        AgentMessage(
            session_id=session_id,
            role="assistant",
            content=content_text,
            risk_level=risk_level,
            references=references,
        )
    )
    await db.commit()
