"""Чтение постов из Telegram-каналов через Telethon (MTProto-юзербот).

Bot API не видит чужие паблики, поэтому используется аккаунт-юзербот.
Сессия создаётся один раз интерактивно (см. `python -m bot.tasks news_login`);
cron-задача работает уже с готовым session-файлом.
"""
from __future__ import annotations

import logging
from datetime import datetime

from telethon import TelegramClient

from bot.services.news.models import Post

logger = logging.getLogger(__name__)


def build_client(api_id: int, api_hash: str, session_path: str) -> TelegramClient:
    """Создаёт Telethon-клиент (без подключения)."""
    return TelegramClient(session_path, api_id, api_hash)


class TelegramReader:
    """Читает посты из каналов за заданное временное окно."""

    def __init__(self, client: TelegramClient) -> None:
        self._client = client

    async def fetch(
        self,
        sources: list[str],
        *,
        since: datetime,
        max_posts: int,
        max_post_chars: int,
    ) -> list[Post]:
        """Собирает посты новее `since` из каждого канала. Возвращает плоский список."""
        posts: list[Post] = []
        for source in sources:
            channel = _normalize(source)
            try:
                posts.extend(
                    await self._fetch_channel(
                        channel, since=since, max_posts=max_posts, max_post_chars=max_post_chars
                    )
                )
            except Exception as exc:  # отдельный канал не должен валить весь сбор
                logger.warning("Не удалось прочитать канал %s: %s", channel, exc)
        return posts

    async def _fetch_channel(
        self, channel: str, *, since: datetime, max_posts: int, max_post_chars: int
    ) -> list[Post]:
        result: list[Post] = []
        async for message in self._client.iter_messages(channel, limit=max_posts):
            msg_date = message.date
            if msg_date is not None and since.tzinfo and msg_date < since:
                break  # сообщения идут от новых к старым — дальше только старее
            text = (message.message or "").strip()
            if not text:
                continue
            result.append(
                Post(
                    channel=channel,
                    msg_id=message.id,
                    date=msg_date,
                    text=text[:max_post_chars],
                )
            )
        return result


def _normalize(source: str) -> str:
    """Приводит источник к username канала (из t.me/<name> или @<name>)."""
    s = source.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/", "@"):
        if s.startswith(prefix):
            s = s[len(prefix) :]
            break
    return s.strip("/")
