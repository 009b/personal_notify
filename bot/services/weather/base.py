"""Общий интерфейс провайдера погоды."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Forecast:
    """Прогноз погоды в нормализованном виде (значения могут отсутствовать)."""

    city: str
    description: str | None = None
    temperature: float | None = None
    feels_like: float | None = None
    wind_speed: float | None = None
    wind_gust: float | None = None
    humidity: float | None = None
    pressure: float | None = None
    precipitation: float | None = None


class WeatherProvider(ABC):
    """Источник прогноза погоды. Реализации скрывают детали конкретного сервиса."""

    @abstractmethod
    async def get_forecast(self) -> Forecast:
        """Возвращает текущий прогноз для заданной локации."""
        raise NotImplementedError
