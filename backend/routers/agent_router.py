from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db
from models.agent import AgentSession
from models.user import User
from schemas.agent_schema import (
    AgentSessionResponse,
    GuideAnswerResponse,
    GuideMessageCreate,
    GuideSessionCreate,
    QaAnswerResponse,
    QaMessageCreate,
    QaSessionCreate,
)
from services.guide_agent_service import create_guide_session, send_guide_message
from services.qa_agent_service import create_qa_session, get_user_session, send_qa_message


router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/qa/sessions", response_model=AgentSessionResponse)
async def create_qa_agent_session(
    payload: QaSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentSession:
    return await create_qa_session(db, current_user, payload)


@router.post("/qa/sessions/{session_id}/messages", response_model=QaAnswerResponse)
async def send_qa_agent_message(
    session_id: int,
    payload: QaMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QaAnswerResponse:
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


@router.get("/sessions/{session_id}", response_model=AgentSessionResponse)
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentSession:
    return await get_user_session(db, current_user.id, session_id, agent_type=None)
