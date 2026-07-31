from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from .models import PERSON_FIELDS, PersonRecord
from .policy import validate_source_url


SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL DEFAULT 'person',
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT '',
    organization TEXT NOT NULL DEFAULT '',
    zip_code TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '',
    country TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    profile_url TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'manual',
    notes TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    consent_basis TEXT NOT NULL DEFAULT '',
    collected_at TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_people_name ON people(name);
CREATE INDEX IF NOT EXISTS idx_people_city ON people(city);
CREATE INDEX IF NOT EXISTS idx_people_org ON people(organization);
"""


class PeopleStore:
    def __init__(self, db_path: str | Path = "data/people.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA)
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(people)").fetchall()}
            if "entity_type" not in columns:
                connection.execute("ALTER TABLE people ADD COLUMN entity_type TEXT NOT NULL DEFAULT 'person'")
            if "zip_code" not in columns:
                connection.execute("ALTER TABLE people ADD COLUMN zip_code TEXT NOT NULL DEFAULT ''")

    def add(self, record: PersonRecord) -> int:
        policy = validate_source_url(record.profile_url, record.entity_type)
        if not policy.allowed:
            raise ValueError(policy.message)
        if not record.name.strip():
            raise ValueError("Name is required.")

        columns = PERSON_FIELDS + ["collected_at"]
        values = [getattr(record, column) for column in columns]
        placeholders = ", ".join("?" for _ in columns)
        sql = f"INSERT INTO people ({', '.join(columns)}) VALUES ({placeholders})"

        with self._connect() as connection:
            cursor = connection.execute(sql, values)
            return int(cursor.lastrowid)

    def add_many(self, records: Iterable[PersonRecord]) -> int:
        count = 0
        with self._connect() as connection:
            for record in records:
                policy = validate_source_url(record.profile_url, record.entity_type)
                if not policy.allowed:
                    raise ValueError(policy.message)
                if not record.name.strip():
                    continue
                columns = PERSON_FIELDS + ["collected_at"]
                values = [getattr(record, column) for column in columns]
                placeholders = ", ".join("?" for _ in columns)
                sql = f"INSERT INTO people ({', '.join(columns)}) VALUES ({placeholders})"
                connection.execute(sql, values)
                count += 1
        return count

    def search(self, query: str = "", limit: int = 1000) -> list[PersonRecord]:
        limit = max(1, min(int(limit), 5000))
        if query.strip():
            needle = f"%{query.strip()}%"
            where = """
            WHERE name LIKE ?
               OR entity_type LIKE ?
               OR role LIKE ?
               OR organization LIKE ?
               OR zip_code LIKE ?
               OR city LIKE ?
               OR country LIKE ?
               OR email LIKE ?
               OR phone LIKE ?
               OR profile_url LIKE ?
               OR source LIKE ?
               OR notes LIKE ?
               OR tags LIKE ?
               OR consent_basis LIKE ?
            """
            params = [needle] * 14 + [limit]
        else:
            where = ""
            params = [limit]

        sql = f"SELECT * FROM people {where} ORDER BY collected_at DESC, id DESC LIMIT ?"
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [PersonRecord.from_mapping(dict(row)) for row in rows]
