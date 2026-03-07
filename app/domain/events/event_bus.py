from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid


class DomainEvent(BaseModel):
    event_id: uuid.UUID
    occurred_on: datetime

    def __init__(self, **data):
        if "event_id" not in data:
            data["event_id"] = uuid.uuid4()
        if "occurred_on" not in data:
            data["occurred_on"] = datetime.now(timezone.utc)
        super().__init__(**data)


class EventBus(ABC):
    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        pass

    @abstractmethod
    def subscribe(self, event_type: type, handler: callable) -> None:
        pass
