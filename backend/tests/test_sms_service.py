from types import SimpleNamespace

from services.sms_service import SmsService


class DummyResponse:
    def __init__(self, status_code: int = 200, json_data: dict | None = None) -> None:
        self.status_code = status_code
        self._json_data = json_data or {}
        self.headers = {"content-type": "application/json"}
        self.text = str(self._json_data)

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._json_data


def make_settings(**overrides):
    data = {
        "sms_debug_code_enabled": False,
        "spug_sms_template_id": "A27L-test",
        "spug_sms_template_name": "PetMall",
        "spug_sms_code_param_name": "code",
        "spug_sms_base_url": "https://push.spug.cc",
        "spug_sms_timeout_seconds": 10.0,
        "sms_code_expire_seconds": 300,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_spug_sms_requires_template_id():
    service = SmsService()
    service.settings = make_settings(spug_sms_template_id="")

    result = service.send_verify_code("13800138000")

    assert result.success is False
    assert "template id" in result.message


def test_spug_sms_posts_template_payload(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return DummyResponse(json_data={"data": {"ok": True}})

    monkeypatch.setattr("services.sms_service.httpx.post", fake_post)

    service = SmsService()
    service.settings = make_settings()
    monkeypatch.setattr(service, "generate_code", lambda: "654321")

    result = service.send_verify_code("13800138000")

    assert result.success is True
    assert result.code == "654321"
    assert captured == {
        "url": "https://push.spug.cc/sms/A27L-test",
        "json": {
            "name": "PetMall",
            "code": "654321",
            "number": "05",
            "to": "13800138000",
        },
        "timeout": 10.0,
    }


def test_spug_sms_supports_custom_code_param_name(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["json"] = json
        return DummyResponse(json_data={"data": {"ok": True}})

    monkeypatch.setattr("services.sms_service.httpx.post", fake_post)

    service = SmsService()
    service.settings = make_settings(spug_sms_code_param_name="verify_code")
    monkeypatch.setattr(service, "generate_code", lambda: "654321")

    result = service.send_verify_code("13800138000")

    assert result.success is True
    assert captured["json"] == {
        "name": "PetMall",
        "verify_code": "654321",
        "number": "05",
        "to": "13800138000",
    }


def test_spug_sms_error_response_fails(monkeypatch):
    def fake_post(url, json, timeout):
        return DummyResponse(json_data={"error": "余额不足"})

    monkeypatch.setattr("services.sms_service.httpx.post", fake_post)

    service = SmsService()
    service.settings = make_settings()

    result = service.send_verify_code("13800138000")

    assert result.success is False
    assert "余额不足" in result.message


def test_spug_sms_non_success_code_fails(monkeypatch):
    def fake_post(url, json, timeout):
        return DummyResponse(json_data={"code": 404, "msg": "模板编码错误"})

    monkeypatch.setattr("services.sms_service.httpx.post", fake_post)

    service = SmsService()
    service.settings = make_settings()

    result = service.send_verify_code("13800138000")

    assert result.success is False
    assert "模板编码错误" in result.message
