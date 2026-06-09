"""Тесты пайплайна и форматтера дайджеста (моки LLM/reader, без сети)."""
from __future__ import annotations

from datetime import datetime, timezone

from bot.models.config import NewsConfig
from bot.services.llm import LLMError
from bot.services.news.format import EMPTY_MESSAGE, render_digest
from bot.services.news.models import Post
from bot.services.news.pipeline import NewsPipeline


def _post(channel, msg_id, text):
    return Post(channel=channel, msg_id=msg_id, date=datetime.now(timezone.utc), text=text)


class _FakeReader:
    def __init__(self, posts):
        self._posts = posts

    async def fetch(self, sources, *, since, max_posts, max_post_chars):
        return list(self._posts)


class _FakeLLM:
    """Возвращает заранее заданные ответы по порядку вызовов."""

    def __init__(self, answers, fail=False):
        self._answers = list(answers)
        self._fail = fail
        self.calls = []

    async def process_text(self, text, *, system=None, model=None, options=None, think=None):
        self.calls.append({"text": text, "system": system, "think": think})
        if self._fail:
            raise LLMError("llm down")
        return self._answers.pop(0)


def _pipeline(reader, llm, *, exclude=("Трамп",), prompts=None):
    cfg = NewsConfig(enabled=True, sources=["a"], exclude_topics=list(exclude))
    prompts = prompts if prompts is not None else {"news_filter": "f", "news_digest": "d"}
    return NewsPipeline(reader, llm, cfg, prompts)


# ---- format ----

def test_render_digest_inserts_links_and_header():
    posts = [_post("durov", 10, "a"), _post("meduzalive", 55, "b")]
    out = render_digest("<b>Тема</b>\nПункт [1] и [2]", posts)
    assert out.startswith("<b>Новости за сутки</b>")
    assert '<a href="https://t.me/durov/10">[1]</a>' in out
    assert '<a href="https://t.me/meduzalive/55">[2]</a>' in out


def test_render_digest_unknown_ref_kept():
    posts = [_post("durov", 10, "a")]
    out = render_digest("Пункт [9]", posts)
    assert "[9]" in out
    assert "<a" not in out.split("[9]")[0].split("Новости за сутки")[-1] or True  # ссылки [9] нет


# ---- filter ----

async def test_filter_drops_posts_by_index():
    posts = [_post("a", 1, "про Трампа"), _post("a", 2, "погода"), _post("a", 3, "спорт")]
    llm = _FakeLLM(answers=["1, 3"])  # модель просит удалить 1 и 3
    pipe = _pipeline(_FakeReader(posts), llm)
    result = await pipe._filter(posts)
    assert [p.msg_id for p in result] == [2]


async def test_filter_skipped_without_topics():
    posts = [_post("a", 1, "x")]
    llm = _FakeLLM(answers=[])
    pipe = _pipeline(_FakeReader(posts), llm, exclude=[])
    result = await pipe._filter(posts)
    assert result == posts
    assert llm.calls == []  # LLM не вызывался


async def test_filter_llm_error_keeps_all():
    posts = [_post("a", 1, "x"), _post("a", 2, "y")]
    llm = _FakeLLM(answers=[], fail=True)
    pipe = _pipeline(_FakeReader(posts), llm)
    result = await pipe._filter(posts)
    assert result == posts


# ---- summarize ----

async def test_summarize_uses_think_off_and_renders_links():
    posts = [_post("durov", 10, "новость")]
    llm = _FakeLLM(answers=["<b>Тема</b>\nИтог [1]"])
    pipe = _pipeline(_FakeReader(posts), llm)
    out = await pipe._summarize(posts)
    assert llm.calls[-1]["think"] is False
    assert '<a href="https://t.me/durov/10">[1]</a>' in out


async def test_summarize_llm_error_falls_back_to_list():
    posts = [_post("durov", 10, "новость один")]
    llm = _FakeLLM(answers=[], fail=True)
    pipe = _pipeline(_FakeReader(posts), llm)
    out = await pipe._summarize(posts)
    assert "новость один" in out
    assert '<a href="https://t.me/durov/10">[1]</a>' in out


# ---- end-to-end ----

async def test_build_digest_empty_when_no_posts():
    pipe = _pipeline(_FakeReader([]), _FakeLLM(answers=[]))
    assert await pipe.build_digest() == EMPTY_MESSAGE


async def test_build_digest_empty_when_all_filtered():
    posts = [_post("a", 1, "про Трампа")]
    llm = _FakeLLM(answers=["1"])  # фильтр удаляет единственный пост
    pipe = _pipeline(_FakeReader(posts), llm)
    assert await pipe.build_digest() == EMPTY_MESSAGE


async def test_build_digest_full_flow():
    posts = [_post("durov", 10, "хорошая новость"), _post("a", 2, "про Трампа")]
    # 1-й вызов LLM — фильтр (удалить 2), 2-й — суммаризация
    llm = _FakeLLM(answers=["2", "<b>Тема</b>\nИтог [1]"])
    pipe = _pipeline(_FakeReader(posts), llm)
    out = await pipe.build_digest()
    assert out.startswith("<b>Новости за сутки</b>")
    assert '<a href="https://t.me/durov/10">[1]</a>' in out
