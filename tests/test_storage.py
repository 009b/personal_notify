"""Тесты хранилища (интерфейс + SQLite + фабрика)."""
from __future__ import annotations

import pytest

from bot.models.config import StorageConfig
from bot.storage import SqliteStorage, build_storage


@pytest.fixture
def storage():
    s = SqliteStorage(":memory:")
    yield s
    s.close()


def test_unseen_by_default(storage):
    assert storage.is_seen("e1") is False


def test_mark_and_check(storage):
    storage.mark_seen("e1")
    assert storage.is_seen("e1") is True
    assert storage.is_seen("e2") is False


def test_mark_is_idempotent(storage):
    storage.mark_seen("e1")
    storage.mark_seen("e1")  # не должно падать (INSERT OR IGNORE)
    assert storage.is_seen("e1") is True


def test_persists_on_disk(tmp_path):
    path = str(tmp_path / "sub" / "notify.db")  # каталог создаётся автоматически
    s1 = SqliteStorage(path)
    s1.mark_seen("e1")
    s1.close()

    s2 = SqliteStorage(path)
    try:
        assert s2.is_seen("e1") is True
    finally:
        s2.close()


def test_build_storage_sqlite():
    s = build_storage(StorageConfig(backend="sqlite", path=":memory:"))
    try:
        assert isinstance(s, SqliteStorage)
    finally:
        s.close()


def test_build_storage_unknown_raises():
    with pytest.raises(ValueError):
        build_storage(StorageConfig(backend="redis", path="x"))
