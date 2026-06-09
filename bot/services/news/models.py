"""Модели данных новостного дайджеста."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Post:
    """Нормализованный пост из Telegram-канала."""

    channel: str
    msg_id: int
    date: datetime
    text: str

    @property
    def url(self) -> str:
        return f"https://t.me/{self.channel}/{self.msg_id}"
