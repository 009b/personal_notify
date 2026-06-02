"""Провайдер погоды Gismeteo: опрос страницы сайта и разбор встроенного JSON.

Данные о текущей погоде встроены в HTML страницы города под ключом `"cw"` (current weather),
где каждое поле — массив значений; берём первый элемент.
"""
from __future__ import annotations

import json
import logging

import httpx

from bot.models.config import WeatherLocation
from bot.services.weather.base import Forecast, WeatherProvider

logger = logging.getLogger(__name__)

# Страница города на Gismeteo. Москва = 4368; для других городов задайте URL под свой код.
DEFAULT_URL = "https://www.gismeteo.ru/weather-moscow-4368/"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "ru",
    "Connection": "close",
}


class GismeteoError(RuntimeError):
    """Ошибка получения или разбора данных Gismeteo."""


class GismeteoProvider(WeatherProvider):
    def __init__(self, location: WeatherLocation, url: str = DEFAULT_URL, timeout: int = 25) -> None:
        self._location = location
        self._url = url
        self._timeout = timeout

    async def get_forecast(self) -> Forecast:
        html = await self._fetch()
        cw = _extract_block(html, '"cw":')
        return self._to_forecast(cw)

    async def _fetch(self) -> str:
        try:
            async with httpx.AsyncClient(timeout=self._timeout, headers=_HEADERS) as client:
                resp = await client.get(self._url)
                resp.raise_for_status()
                return resp.text
        except httpx.HTTPError as exc:
            raise GismeteoError(f"Не удалось загрузить страницу Gismeteo: {exc}") from exc

    def _to_forecast(self, cw: dict) -> Forecast:
        def first(key: str):
            value = cw.get(key)
            if isinstance(value, list):
                return value[0] if value else None
            return value

        return Forecast(
            city=self._location.city,
            description=first("description"),
            temperature=first("temperatureAir"),
            feels_like=first("temperatureFeelsLike"),
            wind_speed=first("windSpeed"),
            wind_gust=first("windGust"),
            humidity=first("humidity"),
            pressure=first("pressure"),
            precipitation=first("precipitation"),
        )


def _extract_block(html: str, marker: str) -> dict:
    """Вырезает сбалансированный JSON-объект, следующий за `marker`, и парсит его."""
    idx = html.find(marker)
    if idx == -1:
        raise GismeteoError(f"В ответе Gismeteo не найден блок {marker}")
    start = html.find("{", idx)
    if start == -1:
        raise GismeteoError(f"После {marker} нет JSON-объекта")

    depth = 0
    for pos in range(start, len(html)):
        char = html[pos]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html[start : pos + 1])
                except json.JSONDecodeError as exc:
                    raise GismeteoError(f"Не удалось разобрать JSON Gismeteo: {exc}") from exc
    raise GismeteoError("Не найден закрывающий блок JSON Gismeteo")
