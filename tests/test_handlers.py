"""Тесты обработчиков команд и сборки диспетчера."""
from __future__ import annotations

from types import SimpleNamespace

import bot.main as main_module
from bot.handlers import common
from bot.main import build_dispatcher
from bot.models.config import AppConfig, Settings


class _Msg:
    def __init__(self):
        self.answers: list[str] = []

    async def answer(self, text):
        self.answers.append(text)


async def test_cmd_start():
    msg = _Msg()
    await common.cmd_start(msg)
    assert msg.answers and "/help" in msg.answers[0]


async def test_cmd_help_lists_commands():
    msg = _Msg()
    await common.cmd_help(msg)
    text = msg.answers[0]
    assert "/start" in text and "/help" in text and "/status" in text


async def test_cmd_status():
    msg = _Msg()
    await common.cmd_status(msg)
    assert msg.answers


def test_build_dispatcher_includes_common_router():
    dp = build_dispatcher(allowed_user_id=123)
    assert "common" in [r.name for r in dp.sub_routers]


async def test_main_starts_polling_and_closes_session(monkeypatch):
    events = []

    class FakeBot:
        def __init__(self, token):
            events.append(("bot", token))
            self.session = SimpleNamespace(close=self._close)

        async def _close(self):
            events.append(("close",))

    class FakeDispatcher:
        async def start_polling(self, bot):
            events.append(("polling",))

    monkeypatch.setattr(main_module, "Bot", FakeBot)
    monkeypatch.setattr(
        main_module, "load_settings",
        lambda: Settings(bot_token="tok", allowed_user_id=1),
    )
    monkeypatch.setattr(main_module, "load_app_config", lambda: AppConfig())
    monkeypatch.setattr(main_module, "build_dispatcher", lambda uid: FakeDispatcher())

    await main_module.main()
    assert ("polling",) in events
    assert ("close",) in events  # сессия закрыта в finally
