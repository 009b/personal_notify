"""Пайплайн новостного дайджеста: collect → filter (LLM) → summarize (LLM) → format."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from bot.models.config import NewsConfig
from bot.services.llm import LLMError, OllamaClient
from bot.services.news.format import EMPTY_MESSAGE, render_digest
from bot.services.news.models import Post
from bot.services.telegram_reader import TelegramReader

logger = logging.getLogger(__name__)

_NUM_RE = re.compile(r"\d+")


class NewsPipeline:
    """Собирает посты, фильтрует и суммаризует их в одну сводку."""

    def __init__(
        self,
        reader: TelegramReader,
        llm: OllamaClient,
        config: NewsConfig,
        prompts: dict[str, str],
    ) -> None:
        self._reader = reader
        self._llm = llm
        self._config = config
        self._prompts = prompts

    async def build_digest(self) -> str:
        """Возвращает готовый текст дайджеста (HTML) или сообщение о пустом результате."""
        posts = await self._collect()
        if not posts:
            return EMPTY_MESSAGE

        posts = await self._filter(posts)
        if not posts:
            return EMPTY_MESSAGE

        return await self._summarize(posts)

    async def _collect(self) -> list[Post]:
        since = datetime.now(timezone.utc) - timedelta(hours=self._config.window_hours)
        return await self._reader.fetch(
            self._config.sources,
            since=since,
            max_posts=self._config.max_posts,
            max_post_chars=self._config.max_post_chars,
        )

    async def _filter(self, posts: list[Post]) -> list[Post]:
        """Убирает посты по нежелательным темам. Отсев детерминированно по индексам."""
        prompt = self._config_prompt("news_filter")
        if not prompt or not self._config.exclude_topics:
            return posts

        numbered = _number_posts(posts)
        topics = ", ".join(self._config.exclude_topics)
        system = f"{prompt}\nНежелательные темы: {topics}."
        try:
            answer = await self._llm.process_text(numbered, system=system, think=False)
        except LLMError as exc:
            logger.warning("Фильтр LLM недоступен, пропускаю фильтрацию: %s", exc)
            return posts

        drop = {int(n) for n in _NUM_RE.findall(answer)}
        return [p for i, p in enumerate(posts, start=1) if i not in drop]

    async def _summarize(self, posts: list[Post]) -> str:
        prompt = self._config_prompt("news_digest")
        if not prompt:
            # Без промпта суммаризации — отдаём простой список со ссылками.
            return render_digest(
                "\n".join(f"{p.text} [{i}]" for i, p in enumerate(posts, start=1)), posts
            )

        numbered = _number_posts(posts)
        try:
            summary = await self._llm.process_text(numbered, system=prompt, think=False)
        except LLMError as exc:
            logger.warning("Суммаризация LLM недоступна, отдаю список постов: %s", exc)
            summary = "\n".join(f"{p.text} [{i}]" for i, p in enumerate(posts, start=1))

        return render_digest(summary, posts)

    def _config_prompt(self, name: str) -> str | None:
        return self._prompts.get(name)


def _number_posts(posts: list[Post]) -> str:
    return "\n".join(f"[{i}] ({p.channel}) {p.text}" for i, p in enumerate(posts, start=1))
