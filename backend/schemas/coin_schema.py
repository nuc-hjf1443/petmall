from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PetCoinAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    balance: int
    frozen_balance: int
    total_earned: int
    total_spent: int
    created_at: datetime
    updated_at: datetime


class PetCoinLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    change_amount: int
    balance_before: int
    balance_after: int
    frozen_before: int
    frozen_after: int
    type: str
    source: str
    related_id: int | None = None
    idempotency_key: str | None = None
    remark: str | None = None
    created_at: datetime


class CheckinResponse(BaseModel):
    checkin_date: date
    reward_amount: int
    account: PetCoinAccountResponse


class CoinTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    reward_amount: int
    task_type: str
    is_enabled: bool
    description: str | None = None
    claimed: bool = False


class CoinTaskClaimResponse(BaseModel):
    task_id: int
    reward_amount: int
    account: PetCoinAccountResponse
