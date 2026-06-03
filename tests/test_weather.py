"""Тесты провайдера погоды Gismeteo, форматтера и фабрики."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

import bot.services.weather.gismeteo as gismeteo_module
from bot.models.config import WeatherLocation
from bot.services.weather import build_provider
from bot.services.weather.base import Forecast
from bot.services.weather.format import format_forecast
from bot.services.weather.gismeteo import GismeteoError, GismeteoProvider

FIXTURE = Path(__file__).parent / "fixtures" / "gismeteo_forecast.json"


def _fixture_data() -> list:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _mock_client(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    orig = gismeteo_module.httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return orig(*args, **kwargs)

    monkeypatch.setattr(gismeteo_module.httpx, "AsyncClient", factory)


def test_to_forecast_from_fixture():
    provider = GismeteoProvider(WeatherLocation(city="Москве"))
    fc = provider._to_forecast(_fixture_data())
    assert fc.city == "Москве"
    # все 4 части суток из прогноза первого дня, округлены до целых
    assert fc.parts_of_day == {
        "night": 15,
        "morning": 19,
        "day": 24,
        "evening": 20,
    }
    assert fc.description == "Ясно"  # cloudiness.scale_3 == 0
    assert fc.humidity == 65


def test_to_forecast_empty_raises():
    with pytest.raises(GismeteoError):
        GismeteoProvider(WeatherLocation())._to_forecast([])


def test_format_forecast_full():
    fc = Forecast(
        city="Москве",
        description="Малооблачно",
        parts_of_day={"night": 14, "morning": 18, "day": 24, "evening": 19},
        wind_speed=3,
        wind_gust=7,
        humidity=36,
        precipitation=0,
    )
    text = format_forecast(fc)
    assert text.startswith("Погода в Москве")
    # описание + ветер + порывы одной смысловой строкой
    assert "Малооблачно, ветер 3 м/с, порывы до 7 м/с" in text
    # все 4 части суток одной строкой, через запятую, в правильном порядке
    assert "Ночь: 14°C, Утро: 18°C, День: 24°C, Вечер: 19°C" in text
    # осадки + влажность одной строкой
    assert "Осадки: 0 мм. Влажность: 36%" in text
    # текущая температура и давление убраны
    assert "Сейчас" not in text
    assert "Давление" not in text


def test_format_forecast_partial_skips_missing():
    fc = Forecast(city="Москве", description="Ясно")
    text = format_forecast(fc)
    assert "Погода в Москве" in text
    assert "Ночь" not in text
    assert "День" not in text
    assert "ветер" not in text
    assert "Влажность" not in text


def test_format_forecast_wind_without_gust():
    fc = Forecast(city="Москве", description="Ясно", wind_speed=2)
    text = format_forecast(fc)
    assert "Ясно, ветер 2 м/с" in text
    assert "порывы" not in text


async def test_get_forecast_fetches_and_parses(monkeypatch):
    data = _fixture_data()

    def handler(request: httpx.Request) -> httpx.Response:
        assert "/api/v2/weather/forecast/" in request.url.path
        return httpx.Response(200, json=data)

    _mock_client(monkeypatch, handler)
    fc = await GismeteoProvider(WeatherLocation(city="Москве")).get_forecast()
    assert fc.parts_of_day["day"] == 24  # округлено
    assert fc.parts_of_day["night"] == 15
    assert fc.city == "Москве"


async def test_get_forecast_network_error_raises(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout")

    _mock_client(monkeypatch, handler)
    with pytest.raises(GismeteoError):
        await GismeteoProvider(WeatherLocation()).get_forecast()


def test_build_provider_gismeteo():
    provider = build_provider("gismeteo", WeatherLocation())
    assert isinstance(provider, GismeteoProvider)


def test_build_provider_unknown_raises():
    with pytest.raises(ValueError):
        build_provider("unknown", WeatherLocation())
