"""Форматирование прогноза в текст оповещения."""
from __future__ import annotations

from bot.services.weather.base import Forecast


def format_forecast(forecast: Forecast) -> str:
    """Шаблонное (без LLM) представление прогноза для отправки в Telegram."""
    lines = [f"Погода в городе {forecast.city}"]
    if forecast.description:
        lines.append(str(forecast.description))
    if forecast.temperature is not None:
        line = f"Температура: {forecast.temperature}°C"
        if forecast.feels_like is not None:
            line += f" (ощущается {forecast.feels_like}°C)"
        lines.append(line)
    if forecast.wind_speed is not None:
        line = f"Ветер: {forecast.wind_speed} м/с"
        if forecast.wind_gust is not None:
            line += f", порывы до {forecast.wind_gust} м/с"
        lines.append(line)
    if forecast.humidity is not None:
        lines.append(f"Влажность: {forecast.humidity}%")
    if forecast.pressure is not None:
        lines.append(f"Давление: {forecast.pressure} мм рт. ст.")
    if forecast.precipitation is not None:
        lines.append(f"Осадки: {forecast.precipitation} мм")
    return "\n".join(lines)
