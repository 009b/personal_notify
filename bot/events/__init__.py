"""События: каркас источников и обработчик."""
from bot.events.base import Event, EventSource
from bot.events.processor import EventProcessor

__all__ = ["Event", "EventSource", "EventProcessor"]
