import sqlite3
from pathlib import Path

from .models import ARTICLES_TABLE_SQL, SOURCES_TABLE_SQL


class DatabaseManager:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.execute("PRAGMA foreign_keys = ON;")
            connection.execute(SOURCES_TABLE_SQL)
            connection.execute(ARTICLES_TABLE_SQL)
