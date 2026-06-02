"""Тесты санитизации HTML для Telegram."""
from __future__ import annotations

from bot.services.telegram_html import sanitize


def test_br_becomes_newline():
    assert sanitize("a<br>b<br/>c<br />d") == "a\nb\nc\nd"


def test_allowed_tags_kept():
    assert sanitize("<b>ж</b> <i>к</i>") == "<b>ж</b> <i>к</i>"


def test_disallowed_tags_removed():
    assert sanitize("<p>текст</p><h1>з</h1>") == "текстз"


def test_attributes_stripped():
    assert sanitize("<b class='x'>ж</b>") == "<b>ж</b>"


def test_bare_special_chars_escaped():
    assert sanitize("5 < 7 & 7 > 3") == "5 &lt; 7 &amp; 7 &gt; 3"


def test_anchor_dropped_but_text_kept():
    assert sanitize("<a href='http://x'>ссылка</a>") == "ссылка"


def test_plain_text_unchanged():
    assert sanitize("Просто текст без тегов") == "Просто текст без тегов"
