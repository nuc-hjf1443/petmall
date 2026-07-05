import secrets
import string
from dataclasses import dataclass
from urllib.parse import quote

import httpx

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

        template_id = self.settings.spug_sms_template_id.strip()
        if not template_id:
            return SmsSendResult(success=False, message="Spug SMS template id is not configured")

        base_url = self.settings.spug_sms_base_url.rstrip("/")
        url = f"{base_url}/sms/{quote(template_id)}"
        code_param_name = self.settings.spug_sms_code_param_name.strip() or "code"
        expire_minutes = max(1, self.settings.sms_code_expire_seconds // 60)
        payload = {
            "name": self.settings.spug_sms_template_name,
            code_param_name: code,
            "number": f"{expire_minutes:02d}",
            "to": phone,
        }
        try:
            response = httpx.post(
                url,
                json=payload,
                timeout=self.settings.spug_sms_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            return SmsSendResult(
                success=False,
                message=f"Spug SMS rejected: HTTP {exc.response.status_code} {exc.response.text[:200]}",
            )
        except httpx.HTTPError as exc:
            return SmsSendResult(success=False, message=f"Spug SMS request failed: {exc}")

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                data = response.json()
            except ValueError:
                return SmsSendResult(success=False, message="Spug SMS response is not valid JSON")
            if isinstance(data, dict) and data.get("error"):
                return SmsSendResult(success=False, message=f"Spug SMS rejected: {data['error']}")
            if isinstance(data, dict) and "code" in data:
                response_code = data.get("code")
                if response_code not in (0, 200, "0", "200", "OK", "ok"):
                    response_message = data.get("msg") or data.get("message") or data
                    return SmsSendResult(
                        success=False,
                        message=f"Spug SMS rejected: {response_message}",
                    )

        return SmsSendResult(success=True, message="SMS sent", code=code)


def get_sms_service() -> SmsService:
    return SmsService()
