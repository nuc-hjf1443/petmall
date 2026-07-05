from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PetProfileBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    pet_type: str = Field(..., min_length=1, max_length=32)
    breed: str | None = Field(default=None, max_length=64)
    gender: str | None = Field(default=None, max_length=16)
    birthday: date | None = None
    arrival_date: date | None = None
    weight: float | None = Field(default=None, ge=0)
    avatar: str | None = Field(default=None, max_length=512)
    sterilized: bool | None = None
    vaccine_status: str | None = Field(default=None, max_length=64)
    deworm_status: str | None = Field(default=None, max_length=64)


class PetProfileCreate(PetProfileBase):
    pass


class PetProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    pet_type: str | None = Field(default=None, min_length=1, max_length=32)
    breed: str | None = Field(default=None, max_length=64)
    gender: str | None = Field(default=None, max_length=16)
    birthday: date | None = None
    arrival_date: date | None = None
    weight: float | None = Field(default=None, ge=0)
    avatar: str | None = Field(default=None, max_length=512)
    sterilized: bool | None = None
    vaccine_status: str | None = Field(default=None, max_length=64)
    deworm_status: str | None = Field(default=None, max_length=64)


class PetDetailProfileUpdate(BaseModel):
    body_size: str | None = Field(default=None, max_length=64)
    health_notes: str | None = None
    allergy_notes: str | None = None
    diet_preference: str | None = None
    product_preference: str | None = None
    behavior_notes: str | None = None
    care_notes: str | None = None


class PetDetailProfileResponse(PetDetailProfileUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    pet_id: int
    profile_completeness: int
    created_at: datetime
    updated_at: datetime


class PetProfileResponse(PetProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    detail_profile: PetDetailProfileResponse | None = None


class PetGrowthRecordCreate(BaseModel):
    record_type: str = Field(..., min_length=1, max_length=32)
    title: str | None = Field(default=None, max_length=128)
    content: str | None = None
    media_urls: list[str] | None = None
    weight: float | None = Field(default=None, ge=0)
    happened_at: datetime | None = None


class PetGrowthRecordResponse(PetGrowthRecordCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    pet_id: int
    created_at: datetime
    updated_at: datetime


class PetHealthReminderCreate(BaseModel):
    reminder_type: str = Field(..., min_length=1, max_length=32)
    title: str = Field(..., min_length=1, max_length=128)
    due_at: datetime
    repeat_rule: str | None = Field(default=None, max_length=64)
    notes: str | None = None


class PetHealthReminderUpdate(BaseModel):
    reminder_type: str | None = Field(default=None, min_length=1, max_length=32)
    title: str | None = Field(default=None, min_length=1, max_length=128)
    due_at: datetime | None = None
    repeat_rule: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, max_length=32)
    notes: str | None = None


class PetHealthReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    pet_id: int
    reminder_type: str
    title: str
    due_at: datetime
    repeat_rule: str | None = None
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class PetProfileCompletenessResponse(BaseModel):
    pet_id: int
    completeness: int
    missing_fields: list[str]


class PetProfileDocumentPreviewResponse(BaseModel):
    pet_id: int
    content: str
    source_snapshot: dict[str, Any]
    profile_completeness: int
