"""Отправка оповещений владельцу в Telegram."""
from __future__ import annotations

from aiogram import Bot


class Notifier:
    """Шлёт сообщения владельцу бота."""

    def __init__(self, bot: Bot, owner_id: int) -> None:
        self._bot = bot
        self._owner_id = owner_id

    async def notify(
        self,
        text: str,
        *,
        parse_mode: str | None = None,
        disable_notification: bool = False,
    ) -> None:
        await self._bot.send_message(
            self._owner_id,
            text,
            parse_mode=parse_mode,
            disable_notification=disable_notification,
        )
