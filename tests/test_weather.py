"""Тесты провайдера погоды Gismeteo, форматтера и фабрики."""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest

import bot.services.weather.gismeteo as gismeteo_module
from bot.models.config import WeatherLocation
from bot.services.weather import build_provider
from bot.services.weather.base import Forecast
from bot.services.weather.format import format_forecast
from bot.services.weather.gismeteo import GismeteoError, GismeteoProvider, _extract_block

FIXTURE = Path(__file__).parent / "fixtures" / "gismeteo_moscow.html"


def test_extract_block_parses_cw():
    html = FIXTURE.read_text(encoding="utf-8")
    cw = _extract_block(html, '"cw":')
    assert cw["temperatureAir"] == [20]
    assert cw["description"] == ["Облачно"]


def test_extract_block_missing_marker_raises():
    with pytest.raises(GismeteoError):
        _extract_block("<html></html>", '"cw":')


def test_gismeteo_to_forecast_from_fixture():
    html = FIXTURE.read_text(encoding="utf-8")
    provider = GismeteoProvider(WeatherLocation(city="Москва"))
    cw = _extract_block(html, '"cw":')
    fc = provider._to_forecast(cw)
    assert fc.city == "Москва"
    assert fc.temperature == 20
    assert fc.feels_like == 17
    assert fc.description == "Облачно"
    assert fc.wind_speed == 5
    assert fc.wind_gust == 7
    assert fc.humidity == 36
    assert fc.pressure == 746
    assert fc.precipitation == 0


def test_format_forecast_full():
    fc = Forecast(
        city="Москва",
        description="Облачно",
        temperature=20,
        feels_like=17,
        wind_speed=5,
        wind_gust=7,
        humidity=36,
        pressure=746,
        precipitation=0,
    )
    text = format_forecast(fc)
    assert "Погода в городе Москва" in text
    assert "Облачно" in text
    assert "20°C" in text and "17°C" in text
    assert "5 м/с" in text and "7 м/с" in text


def test_format_forecast_partial_skips_missing():
    fc = Forecast(city="Москва", temperature=10)
    text = format_forecast(fc)
    assert "10°C" in text
    assert "Ветер" not in text
    assert "Влажность" not in text


async def test_get_forecast_fetches_and_parses(monkeypatch):
    html = FIXTURE.read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    transport = httpx.MockTransport(handler)
    orig = gismeteo_module.httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return orig(*args, **kwargs)

    monkeypatch.setattr(gismeteo_module.httpx, "AsyncClient", factory)
    provider = GismeteoProvider(WeatherLocation(city="Москва"))
    fc = await provider.get_forecast()
    assert fc.temperature == 20
    assert fc.city == "Москва"


async def test_get_forecast_network_error_raises(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout")

    transport = httpx.MockTransport(handler)
    orig = gismeteo_module.httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return orig(*args, **kwargs)

    monkeypatch.setattr(gismeteo_module.httpx, "AsyncClient", factory)
    with pytest.raises(GismeteoError):
        await GismeteoProvider(WeatherLocation()).get_forecast()


def test_build_provider_gismeteo():
    provider = build_provider("gismeteo", WeatherLocation())
    assert isinstance(provider, GismeteoProvider)


def test_build_provider_unknown_raises():
    with pytest.raises(ValueError):
        build_provider("unknown", WeatherLocation())
