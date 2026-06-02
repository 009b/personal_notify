"""Тесты обвязки Ollama с подменой httpx (без сети)."""
from __future__ import annotations

import httpx
import pytest

from bot.models.config import OllamaConfig
from bot.services.llm import LLMError, OllamaClient


def _client_with_handler(handler, **cfg_kwargs) -> OllamaClient:
    """Возвращает OllamaClient, у которого httpx.AsyncClient заменён на MockTransport."""
    transport = httpx.MockTransport(handler)
    cfg = OllamaConfig(base_url="http://test", **cfg_kwargs)
    client = OllamaClient(cfg)

    # Подменяем фабрику AsyncClient внутри модуля
    import bot.services.llm as llm_module

    orig = llm_module.httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return orig(*args, **kwargs)

    llm_module.httpx.AsyncClient = factory  # type: ignore[assignment]
    client._restore = lambda: setattr(llm_module.httpx, "AsyncClient", orig)  # type: ignore[attr-defined]
    return client


async def test_process_text_returns_content():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "  готово  "}})

    client = _client_with_handler(handler)
    try:
        out = await client.process_text("вход", system="sys")
        assert out == "готово"
    finally:
        client._restore()


async def test_process_text_sends_model_and_merged_options():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "ok"}})

    client = _client_with_handler(handler, default_model="m1", options={"temperature": 0.4})
    try:
        await client.process_text("t", system="s", model="m2", options={"top_p": 0.9})
    finally:
        client._restore()

    assert captured["model"] == "m2"
    assert captured["options"] == {"temperature": 0.4, "top_p": 0.9}
    assert captured["stream"] is False
    assert captured["messages"][0] == {"role": "system", "content": "s"}
    assert captured["messages"][1] == {"role": "user", "content": "t"}
    assert "think" not in captured  # по умолчанию не передаётся


async def test_process_text_passes_think_flag():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "ok"}})

    client = _client_with_handler(handler)
    try:
        await client.process_text("t", think=False)
    finally:
        client._restore()

    assert captured["think"] is False


async def test_process_text_http_error_raises_llm_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = _client_with_handler(handler)
    try:
        with pytest.raises(LLMError):
            await client.process_text("x")
    finally:
        client._restore()


async def test_list_models_parses_tags():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": "a"}, {"name": "b"}]})

    client = _client_with_handler(handler)
    try:
        assert await client.list_models() == ["a", "b"]
    finally:
        client._restore()
