import re

from pydantic import BaseModel, Field, field_validator


PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")


def validate_mainland_phone(phone: str) -> str:
    if not PHONE_PATTERN.fullmatch(phone):
        raise ValueError("Invalid mainland China phone number")
    return phone


class SmsCodeRequest(BaseModel):
    phone: str = Field(..., description="Mainland China phone number")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return validate_mainland_phone(value)


class SmsCodeResponse(BaseModel):
    message: str
    debug_code: str | None = None


class RegisterRequest(BaseModel):
    phone: str
    password: str = Field(..., min_length=8, max_length=128)
    sms_code: str = Field(..., min_length=6, max_length=6)
    email: str | None = Field(default=None, max_length=255)
    nickname: str | None = Field(default=None, max_length=64)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return validate_mainland_phone(value)

    @field_validator("sms_code")
    @classmethod
    def validate_sms_code(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("SMS code must contain only digits")
        return value


class LoginRequest(BaseModel):
    account: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
