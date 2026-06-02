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

from bot.config import load_app_config, load_settings
from bot.services.llm import LLMError, OllamaClient
from bot.services.notifier import Notifier
from bot.services.telegram_html import sanitize as sanitize_telegram_html
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
        await Notifier(bot, settings.allowed_user_id).notify(text, parse_mode=parse_mode)
    finally:
        await bot.session.close()


TASKS = {
    "weather": run_weather,
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
