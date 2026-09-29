from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class AppointmentSlot:
    location: str
    available_at: datetime
    source_url: str


class AppointmentProvider(Protocol):
    """Implement only against officially accessible, permitted data sources."""

    async def available_slots(self) -> list[AppointmentSlot]: ...


class NotificationSink(Protocol):
    async def notify(self, slots: list[AppointmentSlot]) -> None: ...
