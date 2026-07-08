from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db
from core.agent_workflow import get_agent_memory_status
from models.database import AsyncSessionLocal
from models.agent import AgentSession
from models.user import User
from schemas.agent_schema import (
    AgentSessionListResponse,
    AgentSessionListItem,
    AgentSessionResponse,
    GuideAnswerResponse,
    GuideMessageCreate,
    GuideRecommendationResponse,
    GuideSessionCreate,
    QaAnswerResponse,
    QaMessageCreate,
    QaSessionCreate,
)
from services.guide_agent_service import create_guide_session, send_guide_message
from services.qa_agent_service import (
    complete_qa_message,
    create_qa_session,
    delete_qa_session,
    get_user_session,
    list_qa_sessions,
    queue_qa_message,
    send_qa_message,
)
from services.guide_agent_service import (
    create_guide_session,
    list_latest_guide_recommendations,
    send_guide_message,
)
from services.qa_agent_service import create_qa_session, get_user_session, list_user_sessions, send_qa_message


router = APIRouter(prefix="/agents", tags=["agents"])


async def finish_qa_message_background(user_id: int, session_id: int, content: str) -> None:
    async with AsyncSessionLocal() as db:
        await complete_qa_message(db, user_id, session_id, content)


@router.get("/memory/status")
async def get_memory_status(
    current_user: User = Depends(get_current_user),
) -> dict:
    return get_agent_memory_status()


@router.post("/qa/sessions", response_model=AgentSessionResponse)
async def create_qa_agent_session(
    payload: QaSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentSession:
    return await create_qa_session(db, current_user, payload)


@router.get("/qa/sessions", response_model=list[AgentSessionListItem])
async def list_qa_agent_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await list_qa_sessions(db, current_user.id)


@router.delete("/qa/sessions/{session_id}")
async def delete_qa_agent_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await delete_qa_session(db, current_user.id, session_id)
    return {"message": "Agent session deleted"}


@router.post("/qa/sessions/{session_id}/messages", response_model=QaAnswerResponse)
async def send_qa_agent_message(
    session_id: int,
    payload: QaMessageCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QaAnswerResponse:
    if payload.async_mode:
        user_message = await queue_qa_message(db, current_user, session_id, payload.content)
        background_tasks.add_task(
            finish_qa_message_background,
            current_user.id,
            session_id,
            payload.content,
        )
        return QaAnswerResponse(
            session_id=session_id,
            user_message=user_message,
            assistant_message=None,
            status="processing",
        )

    user_message, assistant_message = await send_qa_message(db, current_user, session_id, payload.content)
    return QaAnswerResponse(
        session_id=session_id,
        user_message=user_message,
        assistant_message=assistant_message,
    )


@router.post("/guide/sessions", response_model=AgentSessionResponse)
async def create_guide_agent_session(
    payload: GuideSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentSession:
    return await create_guide_session(db, current_user, payload)


@router.get("/sessions", response_model=AgentSessionListResponse)
async def list_agent_sessions(
    agent_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await list_user_sessions(
        db,
        current_user.id,
        agent_type=agent_type,
        page=page,
        page_size=page_size,
    )


@router.post("/guide/sessions/{session_id}/messages", response_model=GuideAnswerResponse)
async def send_guide_agent_message(
    session_id: int,
    payload: GuideMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GuideAnswerResponse:
    user_message, assistant_message, recommendations = await send_guide_message(
        db,
        current_user,
        session_id,
        payload.content,
        payload.limit,
    )
    return GuideAnswerResponse(
        session_id=session_id,
        user_message=user_message,
        assistant_message=assistant_message,
        recommendations=recommendations,
    )


@router.get("/guide/sessions/{session_id}/recommendations", response_model=list[GuideRecommendationResponse])
async def list_guide_session_recommendations(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await list_latest_guide_recommendations(db, current_user, session_id)


@router.get("/sessions/{session_id}", response_model=AgentSessionResponse)
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentSession:
    return await get_user_session(db, current_user.id, session_id, agent_type=None)
