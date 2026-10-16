import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.access_profiles.catalog import CATALOG_BY_CODE


class ProfileWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    active: bool = True
    permissions: list[str] = Field(default_factory=list, max_length=64)

    @field_validator("permissions")
    @classmethod
    def validate_grants(cls, values: list[str]) -> list[str]:
        if len(set(values)) != len(values):
            raise ValueError("duplicate permissions")
        if any(
            code not in CATALOG_BY_CODE or not CATALOG_BY_CODE[code].delegable
            for code in values
        ):
            raise ValueError("unknown or reserved permission")
        return sorted(values)


class ProfileUpdate(ProfileWrite):
    description: str = Field(max_length=500)
    active: bool
    permissions: list[str] = Field(max_length=64)
    version: int = Field(gt=0)


class ProfileRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    active: bool
    version: int
    permissions: list[str]
    system_role: str | None = None
    user_count: int = 0
    created_at: datetime | None = None


class PermissionRead(BaseModel):
    code: str
    module: str
    label: str
    delegable: bool
    classification: str
