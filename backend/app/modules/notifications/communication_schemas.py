"""Read-only operational channel facts; not a conversation or personal inbox."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DeliveryCommunicationRead(BaseModel):
    id: uuid.UUID
    occurrence_id: uuid.UUID
    event_type: Literal["OCCURRENCE_REGISTERED"]
    created_at: datetime
    channel: Literal["WHATSAPP_MOCK"] = "WHATSAPP_MOCK"
    simulation_status: Literal[
        "NOT_ATTEMPTED", "ATTEMPT_CLAIMED", "SIMULATED", "FAILED", "NO_RECIPIENT"
    ]
    processing_status: (
        Literal[
            "PENDING", "PROCESSING", "SUCCEEDED", "RETRYABLE", "TERMINAL", "UNCERTAIN"
        ]
        | None
    )
