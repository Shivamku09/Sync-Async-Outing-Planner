from pydantic import BaseModel, ConfigDict
from uuid import UUID

from app.common.enums import OutboxEventType


class CommandMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    event_id: UUID
    request_id: UUID
    attempt: int = 1
    event_type: OutboxEventType
