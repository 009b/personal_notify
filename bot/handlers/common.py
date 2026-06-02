"""Обработчики команд: /start, /help, /status."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="common")

HELP_TEXT = (
    "Доступные команды:\n"
    "/start — приветствие\n"
    "/help — список команд\n"
    "/status — статус бота"
)


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer("personal_notify на связи. /help — список команд.")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    await message.answer("Бот работает.")
