from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db
from models.user import User
from schemas.order_schema import PaymentResponse
from services.payment_service import (
    build_alipay_page_url,
    confirm_mock_payment,
    create_order_payment,
    get_payment_result,
    process_alipay_notify,
    query_alipay_payment,
)
from repository.order_repository import get_payment_by_trade_no
from core.errors import not_found
from settings.config import get_settings


router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/orders/{order_id}/pay", response_model=PaymentResponse)
async def pay_order(order_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await create_order_payment(db, user.id, order_id)


@router.post("/mock/{out_trade_no}/confirm", response_model=PaymentResponse)
async def mock_confirm(out_trade_no: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await get_payment_result(db, user.id, out_trade_no)
    return await confirm_mock_payment(db, out_trade_no)


@router.get("/alipay/{out_trade_no}/page-pay")
async def alipay_page(out_trade_no: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await get_payment_result(db, user.id, out_trade_no)
    payment = await get_payment_by_trade_no(db, out_trade_no)
    if payment is None:
        raise not_found("Payment not found")
    return RedirectResponse(build_alipay_page_url(payment), status_code=307)


@router.post("/alipay/notify", response_class=PlainTextResponse)
async def alipay_notify(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    await process_alipay_notify(db, dict(form))
    return "success"


@router.get("/alipay/return")
async def alipay_return(out_trade_no: str):
    settings = get_settings()
    return RedirectResponse(f"{settings.public_h5_url}/#/pages/payment/result?out_trade_no={out_trade_no}")


@router.get("/{out_trade_no}/result", response_model=PaymentResponse)
async def payment_result(out_trade_no: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_payment_result(db, user.id, out_trade_no)


@router.post("/{out_trade_no}/query", response_model=PaymentResponse)
async def payment_query(out_trade_no: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await query_alipay_payment(db, user.id, out_trade_no)
