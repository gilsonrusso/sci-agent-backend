from typing import Callable, Dict, List, Type
from app.domain.events.event_bus import EventBus, DomainEvent


class SimpleInMemoryEventBus(EventBus):
    """
    A simple in-memory event bus suitable for single-instance applications
    and testing. In production with multiple workers, this should be replaced
    with Redis, Kafka, or RabbitMQ.
    """

    def __init__(self):
        self._handlers: Dict[Type[DomainEvent], List[Callable[[DomainEvent], None]]] = (
            {}
        )

    def subscribe(
        self, event_type: Type[DomainEvent], handler: Callable[[DomainEvent], None]
    ) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            try:
                # Synchronous dispatch for now, could be async task
                handler(event)
            except Exception as e:
                # In a real system, log error and potentially retry or send to dead letter queue
                print(f"Error handling event {event}: {e}")


# Global instance for the application to use
event_bus = SimpleInMemoryEventBus()
