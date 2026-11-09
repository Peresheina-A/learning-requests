"""Локальная имитация сервиса заявок с хранением в SQLite."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path


def database_path() -> Path:
    # Отдельный путь позволяет проверять приложение на временной базе.
    return Path(
        os.environ.get(
            "LEARNING_REQUESTS_DB", str(Path(__file__).with_name("requests.db"))
        )
    )


def initialize_database() -> None:
    with closing(sqlite3.connect(database_path())) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'created'
            )
            """
        )
        connection.commit()


def create_request(tool: str, reason: str) -> dict:
    with closing(sqlite3.connect(database_path())) as connection:
        cursor = connection.execute(
            "INSERT INTO requests (tool, reason) VALUES (?, ?)", (tool, reason)
        )
        connection.commit()
        return {
            "id": cursor.lastrowid,
            "tool": tool,
            "reason": reason,
            "status": "created",
        }


def get_request(request_id: int) -> dict | None:
    with closing(sqlite3.connect(database_path())) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT id, tool, reason, status FROM requests WHERE id = ?",
            (request_id,),
        ).fetchone()
        return dict(row) if row is not None else None
