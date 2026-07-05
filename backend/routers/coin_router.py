from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db
from models.coin import PetCoinAccount, PetCoinLog
from models.user import User
from schemas.coin_schema import (
    CheckinResponse,
    CoinTaskClaimResponse,
    CoinTaskResponse,
    PetCoinAccountResponse,
    PetCoinLogResponse,
)
from services.coin_service import checkin, claim_task, get_account, get_logs, get_tasks


router = APIRouter(prefix="/coins", tags=["coins"])


@router.get("/account", response_model=PetCoinAccountResponse)
async def get_my_coin_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PetCoinAccount:
    return await get_account(db, user.id)


@router.get("/logs", response_model=list[PetCoinLogResponse])
async def get_my_coin_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PetCoinLog]:
    return await get_logs(db, user.id, page, page_size)


@router.post("/checkin", response_model=CheckinResponse)
async def checkin_today(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckinResponse:
    record, account = await checkin(db, user.id)
    return CheckinResponse(
        checkin_date=record.checkin_date,
        reward_amount=record.reward_amount,
        account=PetCoinAccountResponse.model_validate(account, from_attributes=True),
    )


@router.get("/tasks", response_model=list[CoinTaskResponse])
async def list_my_coin_tasks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CoinTaskResponse]:
    return [
        CoinTaskResponse.model_validate(task, from_attributes=True).model_copy(update={"claimed": claimed})
        for task, claimed in await get_tasks(db, user.id)
    ]


@router.post("/tasks/{task_id}/claim", response_model=CoinTaskClaimResponse)
async def claim_my_coin_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CoinTaskClaimResponse:
    reward_amount, account = await claim_task(db, user.id, task_id)
    return CoinTaskClaimResponse(
        task_id=task_id,
        reward_amount=reward_amount,
        account=PetCoinAccountResponse.model_validate(account, from_attributes=True),
    )
