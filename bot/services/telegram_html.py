"""Санитизация HTML для Telegram.

Telegram поддерживает лишь ограниченный набор тегов. Вывод LLM может содержать
неподдерживаемые теги (например <br>, <p>, <h1>) — они вызывают ошибку парсинга.
Здесь мы оставляем только разрешённые теги, а всё остальное обезвреживаем:
- <br>, </br>, <br/> -> перевод строки;
- прочие неразрешённые теги удаляются;
- «голые» символы <, >, & вне тегов экранируются.
"""
from __future__ import annotations

import re

# Теги, поддерживаемые Telegram (без атрибутов, кроме разрешённых у некоторых).
# Для оповещений достаточно базового набора форматирования.
ALLOWED_TAGS = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del", "code", "pre"}

_TAG_RE = re.compile(r"<(/?)([a-zA-Z0-9]+)([^>]*)>")


def sanitize(text: str) -> str:
    """Возвращает строку, безопасную для отправки в Telegram с parse_mode=HTML."""
    # <br> в любых вариантах -> перевод строки
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)

    out: list[str] = []
    last = 0
    for m in _TAG_RE.finditer(text):
        # текст до тега — экранируем «голые» спецсимволы
        out.append(_escape(text[last : m.start()]))
        last = m.end()

        closing, name, attrs = m.group(1), m.group(2).lower(), m.group(3)
        if name in ALLOWED_TAGS:
            out.append(f"<{closing}{name}>")  # сбрасываем атрибуты ради безопасности
        # неразрешённый тег — пропускаем (удаляем)

    out.append(_escape(text[last:]))
    return "".join(out)


def _escape(chunk: str) -> str:
    return chunk.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
