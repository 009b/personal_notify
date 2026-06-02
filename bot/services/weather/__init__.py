"""Погода: общий интерфейс провайдера и реализации."""
from bot.services.weather.base import Forecast, WeatherProvider
from bot.services.weather.gismeteo import GismeteoProvider

__all__ = ["Forecast", "WeatherProvider", "GismeteoProvider", "build_provider"]


def build_provider(provider: str, location) -> WeatherProvider:
    """Фабрика провайдера погоды по имени из конфига."""
    if provider == "gismeteo":
        return GismeteoProvider(location)
    raise ValueError(f"Неизвестный провайдер погоды: {provider}")
