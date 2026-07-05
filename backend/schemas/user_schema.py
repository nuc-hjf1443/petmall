from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from schemas.auth_schema import validate_mainland_phone


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pet_experience: str | None = None
    living_city: str | None = None
    living_environment: str | None = None
    budget_preference: str | None = None
    preferred_categories: str | None = None
    feeding_philosophy: str | None = None
    allergy_notes: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    email: str | None = None
    nickname: str | None = None
    avatar: str | None = None
    city: str | None = None
    is_admin: bool
    is_merchant: bool
    real_name_status: str
    token_version: int
    created_at: datetime
    updated_at: datetime
    profile: UserProfileResponse | None = None


class UserProfileUpdate(BaseModel):
    email: str | None = Field(default=None, max_length=255)
    nickname: str | None = Field(default=None, max_length=64)
    avatar: str | None = Field(default=None, max_length=512)
    city: str | None = Field(default=None, max_length=64)
    pet_experience: str | None = Field(default=None, max_length=64)
    living_city: str | None = Field(default=None, max_length=64)
    living_environment: str | None = Field(default=None, max_length=128)
    budget_preference: str | None = Field(default=None, max_length=128)
    preferred_categories: str | None = None
    feeding_philosophy: str | None = None
    allergy_notes: str | None = None


class UserAddressCreate(BaseModel):
    receiver_name: str = Field(..., min_length=1, max_length=64)
    receiver_phone: str = Field(..., min_length=1, max_length=20)
    province: str = Field(..., min_length=1, max_length=64)
    city: str = Field(..., min_length=1, max_length=64)
    district: str = Field(..., min_length=1, max_length=64)
    detail_address: str = Field(..., min_length=1, max_length=255)
    postal_code: str | None = Field(default=None, max_length=20)
    is_default: bool = False

    @field_validator("receiver_phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return validate_mainland_phone(value)


class UserAddressUpdate(BaseModel):
    receiver_name: str | None = Field(default=None, min_length=1, max_length=64)
    receiver_phone: str | None = Field(default=None, min_length=1, max_length=20)
    province: str | None = Field(default=None, min_length=1, max_length=64)
    city: str | None = Field(default=None, min_length=1, max_length=64)
    district: str | None = Field(default=None, min_length=1, max_length=64)
    detail_address: str | None = Field(default=None, min_length=1, max_length=255)
    postal_code: str | None = Field(default=None, max_length=20)
    is_default: bool | None = None

    @field_validator("receiver_phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_mainland_phone(value)


class UserAddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receiver_name: str
    receiver_phone: str
    province: str
    city: str
    district: str
    detail_address: str
    postal_code: str | None = None
    is_default: bool
    created_at: datetime
    updated_at: datetime


class AddressSnapshot(BaseModel):
    receiver_name: str
    receiver_phone: str
    province: str
    city: str
    district: str
    detail_address: str
    postal_code: str | None = None
