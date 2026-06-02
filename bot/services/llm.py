"""Обвязка вокруг локальной Ollama: вызов модели для обработки текста."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from bot.models.config import OllamaConfig

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Ошибка обращения к Ollama."""


class OllamaClient:
    """Клиент Ollama. Модель и опции берутся из конфига, могут быть переопределены на вызов."""

    def __init__(self, config: OllamaConfig) -> None:
        self._config = config

    @property
    def default_model(self) -> str:
        return self._config.default_model

    async def list_models(self) -> list[str]:
        """Список доступных моделей (`GET /api/tags`)."""
        url = f"{self._config.base_url}/api/tags"
        async with httpx.AsyncClient(timeout=self._config.request_timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        return [m["name"] for m in data.get("models", [])]

    async def process_text(
        self,
        text: str,
        *,
        system: str | None = None,
        model: str | None = None,
        options: dict[str, Any] | None = None,
        think: bool | None = None,
    ) -> str:
        """Обрабатывает текст через модель и возвращает результат (`POST /api/chat`).

        `think=False` отключает режим рассуждений (быстрее); если None — не передаётся.
        """
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": text})

        payload: dict[str, Any] = {
            "model": model or self._config.default_model,
            "messages": messages,
            "stream": False,
            "options": {**self._config.options, **(options or {})},
        }
        if think is not None:
            payload["think"] = think
        url = f"{self._config.base_url}/api/chat"
        try:
            async with httpx.AsyncClient(timeout=self._config.request_timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise LLMError(f"Ошибка обращения к Ollama: {exc}") from exc

        content = data.get("message", {}).get("content", "")
        return content.strip()
