import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.pagination import PageResponse

Category = Literal["TRIPS", "OCCURRENCES", "SECURITY"]
EventType = Literal["TRIP_STARTED", "OCCURRENCE_REGISTERED"]
EVENT_CATEGORIES = {"TRIP_STARTED": "TRIPS", "OCCURRENCE_REGISTERED": "OCCURRENCES"}


class NotificationRead(BaseModel):
    id: uuid.UUID
    event_type: EventType
    category: Category
    title: str
    summary: str
    created_at: datetime
    received_at: datetime
    read_at: datetime | None


class NotificationPage(PageResponse[NotificationRead]):
    unread_count: int = Field(ge=0)


class UnreadCount(BaseModel):
    unread_count: int = Field(ge=0)


class ReadAllResult(BaseModel):
    updated: int = Field(ge=0)


class NotificationSource(BaseModel):
    href: str


class PreferenceWrite(BaseModel):
    category: Category
    enabled: bool = Field(strict=True)
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def preserve_security(self):
        if self.category == "SECURITY" and not self.enabled:
            raise ValueError(
                "Os avisos obrigatórios de segurança não podem ser desativados."
            )
        return self


class PreferencesWrite(BaseModel):
    items: list[PreferenceWrite] = Field(min_length=1, max_length=3)
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def unique_categories(self):
        if len({item.category for item in self.items}) != len(self.items):
            raise ValueError("Categorias repetidas não são permitidas.")
        return self


class PreferenceRead(PreferenceWrite):
    mandatory: bool


class PreferencesRead(BaseModel):
    items: list[PreferenceRead]
