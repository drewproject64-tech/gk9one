"""Persist GK9's featured /start section; neither mode hides features."""

import sqlite3
from pathlib import Path

MODE_TOOLS = "tools"
MODE_GAMES = "games"
VALID_MODES = frozenset((MODE_TOOLS, MODE_GAMES))


class ModeStore:
    def __init__(self, database_path: str):
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path, timeout=10) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS settings "
                "(name TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )

    def get_mode(self) -> str:
        with sqlite3.connect(self.path, timeout=10) as connection:
            row = connection.execute(
                "SELECT value FROM settings WHERE name=?", ("featured_mode",)
            ).fetchone()
        return row[0] if row and row[0] in VALID_MODES else MODE_TOOLS

    def set_mode(self, mode: str) -> None:
        if mode not in VALID_MODES:
            raise ValueError(f"Invalid featured mode: {mode}")
        with sqlite3.connect(self.path, timeout=10) as connection:
            connection.execute(
                "INSERT INTO settings(name, value) VALUES(?, ?) "
                "ON CONFLICT(name) DO UPDATE SET value=excluded.value",
                ("featured_mode", mode),
            )
