"""Тесты CLI-задачи run_news (моки клиента/пайплайна/бота, без сети)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import bot.tasks as tasks
from bot.config import ConfigError
from bot.models.config import AppConfig, NewsConfig, Settings


class _FakeClient:
    def __init__(self, authorized=True):
        self._authorized = authorized
        self.disconnected = False

    async def connect(self):
        pass

    async def is_user_authorized(self):
        return self._authorized

    async def disconnect(self):
        self.disconnected = True


class _FakeBot:
    instances: list["_FakeBot"] = []

    def __init__(self, token):
        self.sent = []
        self.session = SimpleNamespace(close=self._close)
        _FakeBot.instances.append(self)

    async def send_message(self, chat_id, text, parse_mode=None, disable_notification=False):
        self.sent.append((chat_id, text, parse_mode, disable_notification))

    async def _close(self):
        pass


@pytest.fixture
def _patched(monkeypatch):
    _FakeBot.instances.clear()
    monkeypatch.setattr(tasks, "Bot", _FakeBot)
    monkeypatch.setattr(
        tasks, "load_settings",
        lambda: Settings(
            bot_token="tok", allowed_user_id=99,
            tg_api_id=1, tg_api_hash="h", tg_session_path="x.session",
        ),
    )
    monkeypatch.setattr(tasks, "build_client", lambda *a, **k: _FakeClient())
    return monkeypatch


async def test_run_news_disabled_does_nothing(_patched):
    _patched.setattr(tasks, "load_app_config", lambda: AppConfig(news=NewsConfig(enabled=False)))
    await tasks.run_news()
    assert _FakeBot.instances == []  # бот не создавался


async def test_run_news_sends_digest(_patched):
    _patched.setattr(tasks, "load_app_config", lambda: AppConfig(news=NewsConfig(enabled=True, silent=True)))

    class _FakePipeline:
        def __init__(self, *a, **k):
            pass

        async def build_digest(self):
            return "<b>Новости за сутки</b>\nИтог"

    _patched.setattr(tasks, "NewsPipeline", _FakePipeline)
    await tasks.run_news()
    chat, text, parse_mode, silent = _FakeBot.instances[-1].sent[0]
    assert chat == 99
    assert "Новости за сутки" in text
    assert parse_mode == "HTML"
    assert silent is True


async def test_run_news_unauthorized_raises(_patched):
    _patched.setattr(tasks, "load_app_config", lambda: AppConfig(news=NewsConfig(enabled=True)))
    _patched.setattr(tasks, "build_client", lambda *a, **k: _FakeClient(authorized=False))
    with pytest.raises(ConfigError):
        await tasks.run_news()


async def test_run_news_requires_credentials(_patched):
    _patched.setattr(tasks, "load_app_config", lambda: AppConfig(news=NewsConfig(enabled=True)))
    _patched.setattr(
        tasks, "load_settings",
        lambda: Settings(bot_token="tok", allowed_user_id=99),  # без TG_API_ID/HASH
    )
    with pytest.raises(ConfigError):
        await tasks.run_news()
