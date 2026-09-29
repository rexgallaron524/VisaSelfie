import asyncio
import logging
from dataclasses import dataclass

from app.monitoring.interfaces import AppointmentProvider, NotificationSink

logger = logging.getLogger("visaselfie.monitoring")


@dataclass(frozen=True)
class SchedulerConfig:
    enabled: bool = False
    interval_seconds: int = 3600


async def run_scheduler(
    provider: AppointmentProvider,
    notifications: NotificationSink,
    config: SchedulerConfig,
    stop: asyncio.Event,
) -> None:
    """Not started by the application. No scraping or notifications are configured."""
    if not config.enabled:
        return
    if config.interval_seconds < 300:
        raise ValueError("Monitoring interval must be at least five minutes")
    while not stop.is_set():
        try:
            slots = await provider.available_slots()
            if slots:
                await notifications.notify(slots)
        except Exception as exc:
            logger.warning("Monitoring attempt failed: %s", type(exc).__name__)
        try:
            await asyncio.wait_for(stop.wait(), timeout=config.interval_seconds)
        except TimeoutError:
            pass
