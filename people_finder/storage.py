from __future__ import annotations

import sqlite3
from dataclasses import dataclass
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
    address TEXT NOT NULL DEFAULT '',
    zip_code TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '',
    country TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    website TEXT NOT NULL DEFAULT '',
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
CREATE INDEX IF NOT EXISTS idx_people_url ON people(profile_url);
"""


@dataclass(slots=True)
class AddManySummary:
    imported: int = 0
    skipped_duplicates: int = 0
    skipped_empty: int = 0


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
            if "address" not in columns:
                connection.execute("ALTER TABLE people ADD COLUMN address TEXT NOT NULL DEFAULT ''")
            if "website" not in columns:
                connection.execute("ALTER TABLE people ADD COLUMN website TEXT NOT NULL DEFAULT ''")

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
        return self.add_many_with_summary(records).imported

    def add_many_with_summary(self, records: Iterable[PersonRecord]) -> AddManySummary:
        summary = AddManySummary()
        seen_batch: set[tuple[str, ...]] = set()
        prepared_records = list(records)
        count = 0
        with self._connect() as connection:
            for record in prepared_records:
                policy = validate_source_url(record.profile_url, record.entity_type)
                if not policy.allowed:
                    raise ValueError(policy.message)
                if not record.name.strip():
                    summary.skipped_empty += 1
                    continue
                fingerprint = self._fingerprint(record)
                if fingerprint in seen_batch or self._exists(connection, record):
                    summary.skipped_duplicates += 1
                    continue
                seen_batch.add(fingerprint)
                columns = PERSON_FIELDS + ["collected_at"]
                values = [getattr(record, column) for column in columns]
                placeholders = ", ".join("?" for _ in columns)
                sql = f"INSERT INTO people ({', '.join(columns)}) VALUES ({placeholders})"
                connection.execute(sql, values)
                count += 1
        summary.imported = count
        return summary

    def search(self, query: str = "", limit: int = 1000) -> list[PersonRecord]:
        limit = max(1, min(int(limit), 5000))
        if query.strip():
            needle = f"%{query.strip()}%"
            where = """
            WHERE name LIKE ?
               OR entity_type LIKE ?
               OR role LIKE ?
               OR organization LIKE ?
               OR address LIKE ?
               OR zip_code LIKE ?
               OR city LIKE ?
               OR country LIKE ?
               OR email LIKE ?
               OR phone LIKE ?
               OR website LIKE ?
               OR profile_url LIKE ?
               OR source LIKE ?
               OR notes LIKE ?
               OR tags LIKE ?
               OR consent_basis LIKE ?
            """
            params = [needle] * 16 + [limit]
        else:
            where = ""
            params = [limit]

        sql = f"SELECT * FROM people {where} ORDER BY collected_at DESC, id DESC LIMIT ?"
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [PersonRecord.from_mapping(dict(row)) for row in rows]

    def _exists(self, connection: sqlite3.Connection, record: PersonRecord) -> bool:
        if record.profile_url.strip():
            row = connection.execute(
                "SELECT 1 FROM people WHERE lower(profile_url) = lower(?) LIMIT 1",
                [record.profile_url.strip()],
            ).fetchone()
            if row:
                return True

        row = connection.execute(
            """
            SELECT 1 FROM people
            WHERE lower(entity_type) = lower(?)
              AND lower(name) = lower(?)
              AND lower(zip_code) = lower(?)
              AND lower(city) = lower(?)
            LIMIT 1
            """,
            [record.entity_type.strip(), record.name.strip(), record.zip_code.strip(), record.city.strip()],
        ).fetchone()
        return row is not None

    def _fingerprint(self, record: PersonRecord) -> tuple[str, ...]:
        if record.profile_url.strip():
            return ("url", record.profile_url.strip().lower())
        return (
            "identity",
            record.entity_type.strip().lower(),
            record.name.strip().lower(),
            record.zip_code.strip().lower(),
            record.city.strip().lower(),
        )
