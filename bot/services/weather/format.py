"""Форматирование прогноза в текст оповещения."""
from __future__ import annotations

from bot.services.weather.base import Forecast

# Подписи частей суток в порядке вывода.
_PART_LABELS = [
    ("night", "Ночь"),
    ("morning", "Утро"),
    ("day", "День"),
    ("evening", "Вечер"),
]


def format_forecast(forecast: Forecast) -> str:
    """Шаблонное (без LLM) представление прогноза для отправки в Telegram."""
    lines = [f"Погода в {forecast.city}"]

    # Описание + ветер + порывы — одной смысловой строкой.
    sky = []
    if forecast.description:
        sky.append(str(forecast.description).lower())
    if forecast.wind_speed is not None:
        wind = f"ветер {forecast.wind_speed} м/с"
        if forecast.wind_gust is not None:
            wind += f", порывы до {forecast.wind_gust} м/с"
        sky.append(wind)
    if sky:
        line = ", ".join(sky)
        lines.append(line[0].upper() + line[1:])

    # Температура по частям суток — одной строкой.
    parts = [
        f"{label}: {forecast.parts_of_day[key]}°C"
        for key, label in _PART_LABELS
        if key in forecast.parts_of_day
    ]
    if parts:
        lines.append(", ".join(parts))

    # Осадки + влажность — одной строкой (про влагу).
    moisture = []
    if forecast.precipitation is not None:
        moisture.append(f"Осадки: {forecast.precipitation} мм")
    if forecast.humidity is not None:
        moisture.append(f"Влажность: {forecast.humidity}%")
    if moisture:
        lines.append(". ".join(moisture))

    return "\n".join(lines)
