"""Тесты фильтра доступа, notifier и CLI-задачи weather."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import bot.tasks as tasks
from bot.access import OwnerOnly
from bot.models.config import AppConfig, OllamaConfig, Settings, WeatherConfig
from bot.services.notifier import Notifier
from bot.services.weather.base import Forecast


def _message(user_id: int | None):
    user = SimpleNamespace(id=user_id) if user_id is not None else None
    return SimpleNamespace(from_user=user)


async def test_owner_only_allows_owner():
    flt = OwnerOnly(allowed_user_id=42)
    assert await flt(_message(42)) is True


async def test_owner_only_rejects_others():
    flt = OwnerOnly(allowed_user_id=42)
    assert await flt(_message(7)) is False
    assert await flt(_message(None)) is False


async def test_notifier_sends_to_owner():
    sent = {}

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None, disable_notification=False):
            sent.update(chat_id=chat_id, text=text, parse_mode=parse_mode, silent=disable_notification)

    await Notifier(FakeBot(), owner_id=99).notify("привет")
    assert sent == {"chat_id": 99, "text": "привет", "parse_mode": None, "silent": False}


async def test_notifier_passes_parse_mode_and_silent():
    sent = {}

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None, disable_notification=False):
            sent["parse_mode"] = parse_mode
            sent["silent"] = disable_notification

    await Notifier(FakeBot(), owner_id=1).notify("t", parse_mode="HTML", disable_notification=True)
    assert sent["parse_mode"] == "HTML"
    assert sent["silent"] is True


class _FakeBot:
    instances: list["_FakeBot"] = []

    def __init__(self, token):
        self.token = token
        self.sent: list = []
        self.session = SimpleNamespace(close=self._close)
        _FakeBot.instances.append(self)

    async def send_message(self, chat_id, text, parse_mode=None, disable_notification=False):
        self.sent.append((chat_id, text, parse_mode, disable_notification))

    async def _close(self):
        pass


class _FakeProvider:
    async def get_forecast(self):
        return Forecast(city="Москве", description="Облачно", parts_of_day={"day": 23})


@pytest.fixture
def _patched_tasks(monkeypatch):
    _FakeBot.instances.clear()
    monkeypatch.setattr(tasks, "Bot", _FakeBot)
    monkeypatch.setattr(
        tasks, "load_settings",
        lambda: Settings(bot_token="tok", allowed_user_id=99),
    )
    monkeypatch.setattr(tasks, "build_provider", lambda provider, location: _FakeProvider())
    return monkeypatch


async def test_run_weather_without_llm_sends_template(_patched_tasks):
    _patched_tasks.setattr(
        tasks, "load_app_config",
        lambda: AppConfig(ollama=OllamaConfig(prompts={})),  # без промпта notify -> без LLM
    )
    await tasks.run_weather()
    bot = _FakeBot.instances[-1]
    chat, text, parse_mode, silent = bot.sent[0]
    assert chat == 99
    assert "Москве" in text
    assert parse_mode is None  # без LLM -> без HTML-разметки
    assert silent is False  # silent по умолчанию выключен


async def test_run_weather_uses_llm_with_think_off_and_html(_patched_tasks):
    _patched_tasks.setattr(
        tasks, "load_app_config",
        lambda: AppConfig(ollama=OllamaConfig(prompts={"notify": "оформи"})),
    )
    captured = {}

    async def fake_process(self, text, *, system=None, model=None, options=None, think=None):
        captured["think"] = think
        # модель вернула неподдерживаемый тег <br> -> должен быть санитизирован
        return "<b>Москва</b><br>Облачно"

    _patched_tasks.setattr(tasks.OllamaClient, "process_text", fake_process)
    await tasks.run_weather()
    _chat, text, parse_mode, _silent = _FakeBot.instances[-1].sent[0]
    assert captured["think"] is False
    assert parse_mode == "HTML"
    assert text == "<b>Москва</b>\nОблачно"  # <br> -> перевод строки


async def test_run_weather_silent_mode(_patched_tasks):
    _patched_tasks.setattr(
        tasks, "load_app_config",
        lambda: AppConfig(
            ollama=OllamaConfig(prompts={}),
            weather=WeatherConfig(silent=True),
        ),
    )
    await tasks.run_weather()
    _chat, _text, _pm, silent = _FakeBot.instances[-1].sent[0]
    assert silent is True


async def test_run_weather_llm_failure_falls_back_to_template(_patched_tasks):
    _patched_tasks.setattr(
        tasks, "load_app_config",
        lambda: AppConfig(ollama=OllamaConfig(prompts={"notify": "оформи"})),
    )

    async def fail(self, text, *, system=None, model=None, options=None, think=None):
        raise tasks.LLMError("ollama down")

    _patched_tasks.setattr(tasks.OllamaClient, "process_text", fail)
    await tasks.run_weather()
    _chat, text, parse_mode, _silent = _FakeBot.instances[-1].sent[0]
    assert "Москве" in text  # вернулся шаблонный текст
    assert parse_mode is None  # fallback -> без HTML


def test_cli_main_dispatches_weather(monkeypatch):
    called = {}

    async def fake_weather():
        called["ran"] = True

    monkeypatch.setattr(tasks, "TASKS", {"weather": fake_weather})
    monkeypatch.setattr("sys.argv", ["tasks", "weather"])
    tasks.main()
    assert called.get("ran") is True
