import sqlite3
from pathlib import Path
from typing import Any

from .messages import message_id, zoho_thread_id


class StateStore:
    """Persistent delivery and Zoho-to-Discord conversation mapping."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_messages (
                message_id TEXT PRIMARY KEY,
                zoho_thread_id TEXT NOT NULL,
                processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS discord_threads (
                zoho_thread_id TEXT PRIMARY KEY,
                discord_thread_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.connection.commit()

    @property
    def initialized(self) -> bool:
        row = self.connection.execute(
            "SELECT value FROM settings WHERE key = 'initialized'"
        ).fetchone()
        return row is not None and row[0] == "1"

    def bootstrap(self, messages: list[dict[str, Any]]) -> None:
        with self.connection:
            for message in messages:
                self.connection.execute(
                    """
                    INSERT OR IGNORE INTO processed_messages
                        (message_id, zoho_thread_id)
                    VALUES (?, ?)
                    """,
                    (message_id(message), zoho_thread_id(message)),
                )
            self.connection.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('initialized', '1')"
            )

    def is_processed(self, zoho_message_id: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM processed_messages WHERE message_id = ?",
            (zoho_message_id,),
        ).fetchone()
        return row is not None

    def discord_thread_id(self, zoho_thread: str) -> int | None:
        row = self.connection.execute(
            "SELECT discord_thread_id FROM discord_threads WHERE zoho_thread_id = ?",
            (zoho_thread,),
        ).fetchone()
        return int(row[0]) if row is not None else None

    def forget_discord_thread(self, zoho_thread: str) -> None:
        with self.connection:
            self.connection.execute(
                "DELETE FROM discord_threads WHERE zoho_thread_id = ?",
                (zoho_thread,),
            )

    def complete_message(
        self, zoho_message_id: str, zoho_thread: str, discord_thread_id: int
    ) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT OR REPLACE INTO discord_threads
                    (zoho_thread_id, discord_thread_id)
                VALUES (?, ?)
                """,
                (zoho_thread, discord_thread_id),
            )
            self.connection.execute(
                """
                INSERT OR IGNORE INTO processed_messages
                    (message_id, zoho_thread_id)
                VALUES (?, ?)
                """,
                (zoho_message_id, zoho_thread),
            )

    def close(self) -> None:
        self.connection.close()
