"""Bounded public conversation; context is resolved server-side."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=2000)
    history: list[Message] = Field(default_factory=list, max_length=8)
    diagnostic_token: str | None = Field(default=None, min_length=1, max_length=4096)
    customer_id: uuid.UUID | None = None
    plan_id: uuid.UUID | None = None
    distribution_id: uuid.UUID | None = None


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    page: int = Field(default=1, ge=1, le=1000)
    start: datetime | None = None
    end: datetime | None = None
    customer: str | None = Field(default=None, min_length=2, max_length=160)
    status: (
        Literal["DRAFT", "READY", "PLANNED", "IN_TRANSIT", "DELIVERED", "CANCELED"]
        | None
    ) = None


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Literal[
        "get_registered_products",
        "get_registered_trucks",
        "get_fleet_availability",
        "get_company_summary",
        "get_customer_order_metrics",
        "get_delivery_metrics",
        "get_fleet_utilization",
        "get_financial_impact",
        "get_canceled_distributions",
    ]
    arguments: ToolArguments


class CustomerChoice(BaseModel):
    reference: uuid.UUID
    label: str


class Source(BaseModel):
    filter_label: str | None = None
    choices: list[CustomerChoice] = Field(default_factory=list, max_length=6)
    links: list[dict[str, str]] = Field(default_factory=list, max_length=10)
    name: str
    period_start: datetime | None = None
    period_end: datetime | None = None
    timezone: str = "UTC"
    criteria: str
    values: dict[str, int | float | str | None]


class ChatResponse(BaseModel):
    source: Literal["GROQ", "BACKEND", "FALLBACK", "GUARDRAIL"]
    answer: str
    facts: list[Source] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    links: list[dict[str, str]] = Field(default_factory=list)
