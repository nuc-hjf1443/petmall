import json
import secrets
import string
from dataclasses import dataclass

from settings.config import get_settings


@dataclass(frozen=True)
class SmsSendResult:
    success: bool
    message: str
    code: str | None = None


class SmsService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def generate_code(self) -> str:
        return "".join(secrets.choice(string.digits) for _ in range(6))

    def send_verify_code(self, phone: str) -> SmsSendResult:
        code = self.generate_code()
        if self.settings.sms_debug_code_enabled:
            return SmsSendResult(success=True, message="debug sms code generated", code=code)

        if not self.settings.aliyun_sms_access_key_id or not self.settings.aliyun_sms_access_key_secret:
            return SmsSendResult(success=False, message="Aliyun SMS access key is not configured")
        if not self.settings.aliyun_sms_sign_name:
            return SmsSendResult(success=False, message="Aliyun SMS sign name is not configured")

        try:
            from alibabacloud_dypnsapi20170525 import models as dypnsapi_models
            from alibabacloud_dypnsapi20170525.client import Client as DypnsapiClient
            from alibabacloud_tea_openapi import models as open_api_models
        except ImportError as exc:
            return SmsSendResult(success=False, message=f"Aliyun SMS SDK is not installed: {exc}")

        config = open_api_models.Config(
            access_key_id=self.settings.aliyun_sms_access_key_id,
            access_key_secret=self.settings.aliyun_sms_access_key_secret,
            endpoint=self.settings.aliyun_sms_endpoint,
        )
        client = DypnsapiClient(config)
        template_param = {"code": code, "min": str(self.settings.sms_code_expire_seconds // 60)}
        request = dypnsapi_models.SendSmsVerifyCodeRequest(
            phone_number=phone,
            sign_name=self.settings.aliyun_sms_sign_name,
            template_code=self.settings.aliyun_sms_template_code,
            template_param=json.dumps(template_param),
        )
        try:
            response = client.send_sms_verify_code(request)
        except Exception as exc:
            return SmsSendResult(success=False, message=f"Aliyun SMS SDK call failed: {exc}")

        body = getattr(response, "body", None)
        response_code = getattr(body, "code", None)
        response_message = getattr(body, "message", "")
        if response_code == "OK":
            return SmsSendResult(success=True, message="SMS sent", code=code)
        return SmsSendResult(success=False, message=f"Aliyun SMS rejected: {response_message}")


def get_sms_service() -> SmsService:
    return SmsService()
