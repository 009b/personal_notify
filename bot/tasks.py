"""CLI-задачи для запуска из cron.

Короткоживущий процесс: формирует и отправляет оповещение, затем завершается.
Пример crontab (08:00 МСК):

    CRON_TZ=Europe/Moscow
    0 8 * * * cd /path/to/personal_notify && .venv/bin/python -m bot.tasks weather
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from aiogram import Bot

from bot.config import ConfigError, load_app_config, load_settings
from bot.services.llm import LLMError, OllamaClient
from bot.services.news.pipeline import NewsPipeline
from bot.services.notifier import Notifier
from bot.services.telegram_html import sanitize as sanitize_telegram_html
from bot.services.telegram_reader import TelegramReader, build_client
from bot.services.weather import build_provider
from bot.services.weather.format import format_forecast

logger = logging.getLogger(__name__)


async def run_weather() -> None:
    settings = load_settings()
    config = load_app_config()

    provider = build_provider(config.weather.provider, config.weather.location)
    forecast = await provider.get_forecast()
    text = format_forecast(forecast)
    parse_mode: str | None = None

    # Обработка текста оповещения через LLM (если задан промпт notify).
    # think=False — рассуждения для оформления не нужны и сильно ускоряют ответ.
    # При успехе модель возвращает разметку Telegram HTML -> parse_mode=HTML.
    notify_prompt = config.ollama.prompts.get("notify")
    if notify_prompt:
        llm = OllamaClient(config.ollama)
        try:
            raw = await llm.process_text(text, system=notify_prompt, think=False)
            text = sanitize_telegram_html(raw)
            parse_mode = "HTML"
        except LLMError as exc:
            logger.warning("LLM недоступна, отправляю шаблонный текст: %s", exc)

    bot = Bot(token=settings.bot_token)
    try:
        await Notifier(bot, settings.allowed_user_id).notify(
            text, parse_mode=parse_mode, disable_notification=config.weather.silent
        )
    finally:
        await bot.session.close()


def _require_tg_credentials(settings) -> tuple[int, str]:
    if not settings.tg_api_id or not settings.tg_api_hash:
        raise ConfigError("Для новостей нужны TG_API_ID и TG_API_HASH в .env")
    return settings.tg_api_id, settings.tg_api_hash


async def run_news() -> None:
    settings = load_settings()
    config = load_app_config()

    if not config.news.enabled:
        logger.info("Новостной дайджест выключен (news.enabled=false)")
        return

    api_id, api_hash = _require_tg_credentials(settings)
    client = build_client(api_id, api_hash, settings.tg_session_path)

    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise ConfigError(
                "Telethon-сессия не авторизована. Выполните: python -m bot.tasks news_login"
            )
        reader = TelegramReader(client)
        pipeline = NewsPipeline(reader, OllamaClient(config.ollama), config.news, config.ollama.prompts)
        text = await pipeline.build_digest()
    finally:
        await client.disconnect()

    bot = Bot(token=settings.bot_token)
    try:
        await Notifier(bot, settings.allowed_user_id).notify(
            text, parse_mode="HTML", disable_notification=config.news.silent
        )
    finally:
        await bot.session.close()


async def run_news_login() -> None:
    """Разовый интерактивный вход в Telegram-аккаунт (создаёт session-файл)."""
    settings = load_settings()
    api_id, api_hash = _require_tg_credentials(settings)
    client = build_client(api_id, api_hash, settings.tg_session_path)
    # start() запросит номер телефона и код подтверждения в консоли.
    await client.start()
    me = await client.get_me()
    logger.info("Авторизован как %s (id=%s)", getattr(me, "username", None), getattr(me, "id", None))
    await client.disconnect()


TASKS = {
    "weather": run_weather,
    "news": run_news,
    "news_login": run_news_login,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI-задачи personal_notify для cron")
    parser.add_argument("task", choices=sorted(TASKS), help="имя задачи")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(TASKS[args.task]())


if __name__ == "__main__":
    main()
