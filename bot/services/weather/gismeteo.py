"""Провайдер погоды Gismeteo через открытый JSON-эндпоинт.

Сайт Gismeteo отдаёт прогноз без токена по адресу
`https://www.gismeteo.ru/api/v2/weather/forecast/<city_id>/` — это тот же поток данных,
что виден на странице города неавторизованному пользователю.

Ответ — список точек: `kind="Obs"` (текущее наблюдение) и `kind="Frc"` (прогноз)
с `tod` (part of day): 0 — ночь, 1 — утро, 2 — день, 3 — вечер.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict

import httpx

from bot.models.config import WeatherLocation
from bot.services.weather.base import Forecast, WeatherProvider

logger = logging.getLogger(__name__)

# ID города на Gismeteo (Москва = 4368). Для другого города задайте свой id.
DEFAULT_CITY_ID = 4368
API_URL = "https://www.gismeteo.ru/api/v2/weather/forecast/{city_id}/"

# tod -> часть суток (порядок сохраняется: ночь, утро, день, вечер)
TOD_NAMES = {0: "night", 1: "morning", 2: "day", 3: "evening"}

# cloudiness.scale_3 -> описание
_CLOUDINESS = {0: "Ясно", 1: "Малооблачно", 2: "Облачно", 3: "Пасмурно"}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "ru",
}


class GismeteoError(RuntimeError):
    """Ошибка получения или разбора данных Gismeteo."""


class GismeteoProvider(WeatherProvider):
    def __init__(
        self,
        location: WeatherLocation,
        city_id: int = DEFAULT_CITY_ID,
        timeout: int = 25,
    ) -> None:
        self._location = location
        self._city_id = city_id
        self._timeout = timeout

    async def get_forecast(self) -> Forecast:
        data = await self._fetch()
        return self._to_forecast(data)

    async def _fetch(self) -> list:
        url = API_URL.format(city_id=self._city_id)
        try:
            async with httpx.AsyncClient(timeout=self._timeout, headers=_HEADERS) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            raise GismeteoError(f"Не удалось загрузить прогноз Gismeteo: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise GismeteoError(f"Не удалось разобрать JSON Gismeteo: {exc}") from exc

    def _to_forecast(self, data: list) -> Forecast:
        if not isinstance(data, list) or not data:
            raise GismeteoError("Пустой ответ Gismeteo")

        current = _first(data, lambda x: x.get("kind") == "Obs")
        forecasts = [x for x in data if x.get("kind") == "Frc" and x.get("tod") is not None]

        # Температуру по частям суток берём из первого дня прогноза, где они есть.
        by_day: dict[str, dict[int, float]] = defaultdict(dict)
        for x in forecasts:
            day = _local_date(x)
            tod = x["tod"]
            if tod not in by_day[day]:
                by_day[day][tod] = _air(x)
        parts_of_day: dict[str, float] = {}
        for day in sorted(by_day):
            parts = by_day[day]
            for tod, name in TOD_NAMES.items():
                value = parts.get(tod)
                if value is not None:
                    parts_of_day[name] = round(value)  # без десятых
            if parts_of_day:
                break

        base = current or (forecasts[0] if forecasts else None)
        if base is None:
            raise GismeteoError("В ответе Gismeteo нет данных о погоде")

        return Forecast(
            city=self._location.city,
            description=_describe(base),
            parts_of_day=parts_of_day,
            wind_speed=_path(base, "wind", "speed", "m_s"),
            wind_gust=_path(base, "wind", "gust_speed", "m_s"),
            humidity=_humidity(forecasts),
            precipitation=_path(base, "precipitation", "amount"),
        )


def _first(items: list, pred) -> dict | None:
    for x in items:
        if pred(x):
            return x
    return None


def _local_date(item: dict) -> str:
    return str(item.get("date", {}).get("local", ""))[:10]


def _air(item: dict) -> float | None:
    return _path(item, "temperature", "air", "C")


def _describe(item: dict) -> str | None:
    scale = _path(item, "cloudiness", "scale_3")
    return _CLOUDINESS.get(scale) if scale is not None else None


def _humidity(forecasts: list) -> float | None:
    if not forecasts:
        return None
    return _path(forecasts[0], "humidity", "percent")


def _path(item: dict, *keys):
    """Безопасно достаёт вложенное значение по цепочке ключей."""
    cur = item
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur
