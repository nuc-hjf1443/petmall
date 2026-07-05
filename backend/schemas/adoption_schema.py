from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdoptionPetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    species: str = Field(..., min_length=1, max_length=32)
    breed: str | None = Field(default=None, max_length=64)
    age_text: str | None = Field(default=None, max_length=64)
    gender: str | None = Field(default=None, max_length=16)
    city: str = Field(..., min_length=1, max_length=64)
    description: str = Field(..., min_length=1)
    health_status: str | None = None
    requirements: str | None = None
    cover_image: str | None = Field(default=None, max_length=512)


class AdoptionPetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    publisher_id: int
    name: str
    species: str
    breed: str | None = None
    age_text: str | None = None
    gender: str | None = None
    city: str
    description: str
    health_status: str | None = None
    requirements: str | None = None
    cover_image: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class AdoptionApplicationCreate(BaseModel):
    contact_name: str = Field(..., min_length=1, max_length=64)
    contact_phone: str = Field(..., min_length=1, max_length=20)
    living_city: str = Field(..., min_length=1, max_length=64)
    living_condition: str = Field(..., min_length=1, max_length=128)
    experience: str | None = None
    reason: str = Field(..., min_length=1)


class AdoptionApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    adoption_pet_id: int
    applicant_id: int
    contact_name: str
    contact_phone: str
    living_city: str
    living_condition: str
    experience: str | None = None
    reason: str
    status: str
    audit_reason: str | None = None
    audited_by: int | None = None
    audited_at: str | None = None
    created_at: datetime
    updated_at: datetime


class AuditDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)
