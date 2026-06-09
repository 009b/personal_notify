"""Форматирование новостного дайджеста для Telegram."""
from __future__ import annotations

import re

from bot.services.news.models import Post
from bot.services.telegram_html import sanitize

HEADER = "Новости за сутки"
EMPTY_MESSAGE = "За последние сутки новостей нет"

_REF_RE = re.compile(r"\[(\d+)\]")


def render_digest(summary: str, posts: list[Post]) -> str:
    """Собирает финальный HTML: санитизация модели + ссылки на источники.

    `posts` пронумерованы с 1 в том же порядке, что подавались модели. Ссылки `[N]`
    в тексте заменяются на HTML-ссылку на исходный пост — уже ПОСЛЕ санитизации,
    чтобы тег <a> не был вырезан (sanitize не пропускает <a>/атрибуты).
    """
    safe = sanitize(f"{HEADER}\n{summary.strip()}")

    def repl(match: re.Match) -> str:
        idx = int(match.group(1))
        if 1 <= idx <= len(posts):
            return f'<a href="{posts[idx - 1].url}">[{idx}]</a>'
        return match.group(0)  # неизвестный номер — оставляем как есть

    body = _REF_RE.sub(repl, safe)
    # Заголовок делаем жирным (он добавлен до санитизации как обычный текст).
    return body.replace(HEADER, f"<b>{HEADER}</b>", 1)
