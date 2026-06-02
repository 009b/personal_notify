"""Реализация хранилища на SQLite (stdlib `sqlite3`)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from bot.storage.base import Storage


class SqliteStorage(Storage):
    """Хранит обработанные события в таблице SQLite.

    Путь `:memory:` создаёт временную БД в памяти (удобно для тестов).
    """

    def __init__(self, path: str) -> None:
        self._path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS seen_events ("
            "key TEXT PRIMARY KEY, "
            "created_at TEXT NOT NULL DEFAULT (datetime('now'))"
            ")"
        )
        self._conn.commit()

    def is_seen(self, key: str) -> bool:
        cur = self._conn.execute("SELECT 1 FROM seen_events WHERE key = ?", (key,))
        return cur.fetchone() is not None

    def mark_seen(self, key: str) -> None:
        self._conn.execute("INSERT OR IGNORE INTO seen_events (key) VALUES (?)", (key,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
