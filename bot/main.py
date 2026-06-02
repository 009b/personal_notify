"""Точка входа демона: инициализация и запуск polling."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.access import OwnerOnly
from bot.config import load_app_config, load_settings
from bot.handlers import common


def build_dispatcher(allowed_user_id: int) -> Dispatcher:
    """Создаёт Dispatcher с подключёнными роутерами и фильтром доступа."""
    dp = Dispatcher()
    owner_only = OwnerOnly(allowed_user_id)
    common.router.message.filter(owner_only)
    dp.include_router(common.router)
    return dp


async def main() -> None:
    settings = load_settings()
    load_app_config()  # валидация конфига на старте

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    bot = Bot(token=settings.bot_token)
    dp = build_dispatcher(settings.allowed_user_id)

    logging.getLogger(__name__).info("Запуск polling")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
