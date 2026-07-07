import base64
import json
from typing import Any
from urllib.parse import quote_plus
from uuid import uuid4

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import bad_request, conflict, not_found
from models.base import utc_now
from models.order import OrderStatus, PaymentStatus, PaymentTransaction
from repository.order_repository import (
    get_order,
    get_payment_by_business,
    get_payment_by_trade_no,
)
from schemas.order_schema import PaymentResponse
from services.order_service import mark_order_paid
from settings.config import get_settings


SENSITIVE_FIELDS = {"sign", "buyer_id", "buyer_logon_id", "receipt_amount", "invoice_amount"}


def _sanitize(data: dict[str, Any]) -> dict[str, Any]:
    return {key: ("***" if key in SENSITIVE_FIELDS else str(value)[:500]) for key, value in data.items()}


def _canonical(params: dict[str, Any]) -> str:
    return "&".join(f"{key}={value}" for key, value in sorted(params.items()) if value not in (None, ""))


def _normalize_pem(value: str, key_type: str) -> bytes:
    normalized = value.strip().replace("\\n", "\n")
    if "-----BEGIN " in normalized:
        return normalized.encode()
    body = "".join(normalized.split())
    lines = "\n".join(body[index : index + 64] for index in range(0, len(body), 64))
    return f"-----BEGIN {key_type}-----\n{lines}\n-----END {key_type}-----\n".encode()


def _load_private_key(private_key_text: str):
    errors: list[Exception] = []
    for key_type in ("PRIVATE KEY", "RSA PRIVATE KEY"):
        try:
            return serialization.load_pem_private_key(
                _normalize_pem(private_key_text, key_type),
                password=None,
            )
        except ValueError as exc:
            errors.append(exc)
    raise conflict("Alipay private key format is invalid")


def _load_public_key(public_key_text: str):
    errors: list[Exception] = []
    for key_type in ("PUBLIC KEY", "RSA PUBLIC KEY"):
        try:
            return serialization.load_pem_public_key(_normalize_pem(public_key_text, key_type))
        except ValueError as exc:
            errors.append(exc)
    raise bad_request("Alipay public key format is invalid")


def _sign(content: str, private_key_text: str) -> str:
    key = _load_private_key(private_key_text)
    signature = key.sign(content.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode()


def _verify_signature_content(content: str, signature: str, public_key_text: str) -> bool:
    if not signature or not public_key_text:
        return False
    try:
        key = _load_public_key(public_key_text)
        key.verify(
            base64.b64decode(signature),
            content.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def verify_alipay_signature(params: dict[str, Any], public_key_text: str) -> bool:
    signature = params.get("sign")
    if not signature or not public_key_text:
        return False
    unsigned = {key: value for key, value in params.items() if key not in {"sign", "sign_type"}}
    return _verify_signature_content(_canonical(unsigned), str(signature), public_key_text)


def _extract_signed_response(payload: str, response_key: str) -> tuple[dict[str, Any], str]:
    marker = json.dumps(response_key)
    key_start = payload.find(marker)
    if key_start < 0:
        raise bad_request("Invalid Alipay response")
    start = payload.find(":", key_start + len(marker))
    if start < 0:
        raise bad_request("Invalid Alipay response")
    start += 1
    while start < len(payload) and payload[start].isspace():
        start += 1
    body, end = json.JSONDecoder().raw_decode(payload, start)
    envelope = json.loads(payload)
    signature = str(envelope.get("sign", ""))
    if not isinstance(body, dict) or not _verify_signature_content(
        payload[start:end], signature, get_settings().alipay_public_key
    ):
        raise bad_request("Invalid Alipay response signature")
    return body, signature


def _payment_response(payment: PaymentTransaction, pay_url: str | None = None) -> PaymentResponse:
    return PaymentResponse(
        out_trade_no=payment.out_trade_no,
        order_id=payment.business_id,
        business_type=payment.business_type,
        amount=payment.amount,
        status=payment.status,
        payment_mode=payment.payment_mode,
        pay_url=pay_url,
        channel_trade_no=payment.channel_trade_no,
    )


def build_alipay_page_url(payment: PaymentTransaction) -> str:
    settings = get_settings()
    if (
        not settings.alipay_app_id
        or not settings.alipay_private_key
        or not settings.alipay_seller_id
    ):
        raise conflict("Alipay sandbox is not configured")
    params = {
        "app_id": settings.alipay_app_id,
        "method": "alipay.trade.page.pay",
        "format": "JSON",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": utc_now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "notify_url": settings.alipay_notify_url,
        "return_url": settings.alipay_return_url,
        "biz_content": json.dumps(
            {
                "out_trade_no": payment.out_trade_no,
                "total_amount": f"{payment.amount / 100:.2f}",
                "subject": f"PetMall {payment.business_type} {payment.business_id}",
                "product_code": "FAST_INSTANT_TRADE_PAY",
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    }
    params["sign"] = _sign(_canonical(params), settings.alipay_private_key)
    return settings.alipay_gateway_url + "?" + "&".join(
        f"{quote_plus(key)}={quote_plus(str(value))}" for key, value in params.items()
    )


async def create_order_payment(db: AsyncSession, user_id: int, order_id: int) -> PaymentResponse:
    settings = get_settings()
    if settings.payment_mode not in {"mock", "alipay_sandbox"}:
        raise conflict("Unsupported payment mode")
    if settings.payment_mode == "mock" and not settings.mock_payment_enabled:
        raise conflict("Mock payment is disabled")
    order = await get_order(db, order_id, user_id)
    if order is None:
        raise not_found("Order not found")
    if order.status != OrderStatus.PENDING_PAYMENT.value:
        raise conflict("Order is not pending payment")
    payment = await get_payment_by_business(db, order.id)
    if payment is None:
        payment = PaymentTransaction(
            out_trade_no=f"PAY{utc_now():%Y%m%d%H%M%S}{uuid4().hex[:14].upper()}",
            business_type="order",
            business_id=order.id,
            pay_channel=settings.payment_mode,
            payment_mode=settings.payment_mode,
            amount=order.pay_amount,
            status=PaymentStatus.CREATED.value,
        )
        db.add(payment)
        try:
            await db.commit()
            await db.refresh(payment)
        except IntegrityError:
            await db.rollback()
            payment = await get_payment_by_business(db, order.id)
            if payment is None:
                raise
    pay_url = build_alipay_page_url(payment) if settings.payment_mode == "alipay_sandbox" else None
    return _payment_response(payment, pay_url)


async def get_payment_result(db: AsyncSession, user_id: int, out_trade_no: str) -> PaymentResponse:
    payment = await get_payment_by_trade_no(db, out_trade_no)
    if payment is None:
        raise not_found("Payment not found")
    if payment.business_type == "order":
        if await get_order(db, payment.business_id, user_id) is None:
            raise not_found("Payment not found")
    elif payment.business_type == "wallet_recharge":
        from services.wallet_service import ensure_payment_owner

        if not await ensure_payment_owner(db, payment, user_id):
            raise not_found("Payment not found")
    else:
        raise not_found("Payment not found")
    return _payment_response(payment)


async def _complete_payment(
    db: AsyncSession, payment: PaymentTransaction, channel_trade_no: str, raw: dict[str, Any]
) -> PaymentResponse:
    if payment.business_type == "wallet_recharge":
        from services.wallet_service import complete_wallet_recharge

        return await complete_wallet_recharge(db, payment, channel_trade_no, _sanitize(raw))
    if payment.business_type != "order":
        raise conflict("Unsupported payment business type")
    if payment.status == PaymentStatus.PAID.value:
        return _payment_response(payment)
    order = await get_order(db, payment.business_id, lock=True)
    if order is None:
        raise not_found("Order not found")
    if order.status == OrderStatus.CANCELLED.value:
        raise conflict("Cancelled order cannot be paid")
    await mark_order_paid(db, order.id)
    payment.status = PaymentStatus.PAID.value
    payment.channel_trade_no = channel_trade_no
    payment.raw_notify = _sanitize(raw)
    payment.paid_at = utc_now()
    await db.commit()
    return _payment_response(payment)


async def confirm_mock_payment(db: AsyncSession, out_trade_no: str) -> PaymentResponse:
    settings = get_settings()
    if not settings.mock_payment_enabled:
        raise conflict("Mock payment is unavailable")
    payment = await get_payment_by_trade_no(db, out_trade_no, lock=True)
    if payment is None:
        raise not_found("Payment not found")
    if payment.payment_mode != "mock":
        raise conflict("Payment is not a mock payment")
    return await _complete_payment(db, payment, f"MOCK-{out_trade_no}", {"source": "mock"})


async def process_alipay_notify(db: AsyncSession, params: dict[str, Any]) -> None:
    settings = get_settings()
    if not verify_alipay_signature(params, settings.alipay_public_key):
        raise bad_request("Invalid Alipay signature")
    payment = await get_payment_by_trade_no(db, str(params.get("out_trade_no", "")), lock=True)
    if payment is None:
        raise not_found("Payment not found")
    if params.get("app_id") != settings.alipay_app_id:
        raise bad_request("Alipay app id mismatch")
    if not settings.alipay_seller_id or params.get("seller_id") != settings.alipay_seller_id:
        raise bad_request("Alipay seller id mismatch")
    if params.get("total_amount") != f"{payment.amount / 100:.2f}":
        raise bad_request("Payment amount mismatch")
    if params.get("trade_status") not in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
        return
    await _complete_payment(db, payment, str(params.get("trade_no", "")), params)


async def query_alipay_payment(db: AsyncSession, user_id: int, out_trade_no: str) -> PaymentResponse:
    payment = await get_payment_by_trade_no(db, out_trade_no, lock=True)
    if payment is None:
        raise not_found("Payment not found")
    await get_payment_result(db, user_id, out_trade_no)
    settings = get_settings()
    if payment.payment_mode != "alipay_sandbox":
        return _payment_response(payment)
    if not settings.alipay_app_id or not settings.alipay_private_key:
        raise conflict("Alipay sandbox is not configured")
    if payment.business_type == "order" and await get_order(db, payment.business_id, user_id) is None:
        raise not_found("Payment not found")
    params = {
        "app_id": settings.alipay_app_id,
        "method": "alipay.trade.query",
        "format": "JSON",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": utc_now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "biz_content": json.dumps({"out_trade_no": out_trade_no}, separators=(",", ":")),
    }
    params["sign"] = _sign(_canonical(params), settings.alipay_private_key)
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(settings.alipay_gateway_url, data=params)
        response.raise_for_status()
        body, _ = _extract_signed_response(response.text, "alipay_trade_query_response")
    if body.get("code") != "10000":
        return _payment_response(payment)
    if body.get("trade_status") in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
        if body.get("out_trade_no") != payment.out_trade_no:
            raise bad_request("Alipay trade number mismatch")
        if body.get("total_amount") != f"{payment.amount / 100:.2f}":
            raise bad_request("Payment amount mismatch")
        if settings.alipay_seller_id and body.get("seller_id") != settings.alipay_seller_id:
            raise bad_request("Alipay seller id mismatch")
        return await _complete_payment(db, payment, str(body.get("trade_no", "")), body)
    return _payment_response(payment)
