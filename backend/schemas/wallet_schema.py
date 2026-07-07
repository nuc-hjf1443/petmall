from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from schemas.order_schema import PaymentResponse


class WalletAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    balance: int
    frozen_balance: int
    total_recharged: int
    total_withdrawn: int


class WalletRechargeCreate(BaseModel):
    amount: int = Field(..., ge=100, le=500_000)
    payment_mode: str = Field(default="mock", pattern="^(mock|alipay_sandbox)$")


class WalletRechargeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recharge_no: str
    amount: int
    status: str
    paid_at: datetime | None
    created_at: datetime


class WalletRechargePaymentResponse(BaseModel):
    recharge: WalletRechargeResponse
    payment: PaymentResponse


class WithdrawalCreate(BaseModel):
    amount: int = Field(..., ge=100, le=500_000)
    account_name: str = Field(..., min_length=2, max_length=64)
    alipay_account: str = Field(..., min_length=3, max_length=128)


class WithdrawalReviewRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class WithdrawalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    withdrawal_no: str
    user_id: int
    amount: int
    account_name: str
    alipay_account: str
    status: str
    reason: str | None
    reviewed_by: int | None
    reviewed_at: datetime | None
    created_at: datetime


class WalletTransactionResponse(BaseModel):
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
    related_id: int | None
    remark: str | None
    created_at: datetime


class AdminWithdrawalListResponse(BaseModel):
    items: list[WithdrawalResponse]
    total: int
    page: int
    page_size: int
