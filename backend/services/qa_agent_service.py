from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.agent_workflow import run_qa_agent_workflow
from core.errors import not_found
from models.agent import AgentMessage, AgentSession
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


async def get_user_session(db: AsyncSession, user_id: int, session_id: int) -> AgentSession:
    result = await db.execute(
        select(AgentSession)
        .options(selectinload(AgentSession.messages))
        .where(
            AgentSession.id == session_id,
            AgentSession.user_id == user_id,
            AgentSession.agent_type == "qa",
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise not_found("Agent session not found")
    return session


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


async def send_qa_message(
    db: AsyncSession,
    user: User,
    session_id: int,
    content: str,
) -> tuple[AgentMessage, AgentMessage]:
    session = await get_user_session(db, user.id, session_id)
    risk_level = assess_risk(content)
    workflow_result = await run_qa_agent_workflow(
        question=content,
        risk_level=risk_level,
        history=_messages_to_history(session.messages),
        session_id=session_id,
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
        content=workflow_result["answer"],
        risk_level=risk_level,
        references=workflow_result.get("references"),
    )
    db.add_all([user_message, assistant_message])
    await db.commit()
    await db.refresh(user_message)
    await db.refresh(assistant_message)
    return user_message, assistant_message
