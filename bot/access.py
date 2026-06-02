"""Фильтр доступа: пропускать только владельца (whitelist по user_id)."""
from __future__ import annotations

from aiogram.filters import Filter
from aiogram.types import Message


class OwnerOnly(Filter):
    """Пропускает апдейты только от владельца бота."""

    def __init__(self, allowed_user_id: int) -> None:
        self.allowed_user_id = allowed_user_id

    async def __call__(self, message: Message) -> bool:
        return message.from_user is not None and message.from_user.id == self.allowed_user_id
