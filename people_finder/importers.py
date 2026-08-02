from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from .models import PERSON_FIELDS, PersonRecord
from .policy import validate_headers


def records_from_csv_text(csv_text: str) -> list[PersonRecord]:
    reader = csv.DictReader(StringIO(csv_text))
    if not reader.fieldnames:
        return []

    # VIKTIGT – BEHÅLL DENNA KONTROLL: kör validate_headers (SENSITIVE_FIELD_HINTS i
    # policy.py) mot CSV-kolumnrubrikerna innan någon rad importeras. Tas denna bort kan
    # CSV-filer med kolumner som personnummer/ssn/health/bank osv. importeras rakt in i
    # databasen utan att blockeras. Den här kontrollen är korrekt konfigurerad idag och
    # är helt oberoende av person/företag-buggen i policy.py:s validate_source_url.
    policy = validate_headers(list(reader.fieldnames))
    if not policy.allowed:
        raise ValueError(policy.message)

    records: list[PersonRecord] = []
    for row in reader:
        # Bra kod: bygger raden från PERSON_FIELDS (samma DRY-mönster som i storage.py/
        # cli.py) och hoppar tyst över rader utan namn istället för att krascha hela
        # importen på en enda ofullständig rad.
        payload = {field: row.get(field, "") for field in PERSON_FIELDS}
        if payload["name"].strip():
            records.append(PersonRecord.from_mapping(payload))
    return records


def records_from_csv_file(path: str | Path) -> list[PersonRecord]:
    csv_text = Path(path).read_text(encoding="utf-8-sig")
    return records_from_csv_text(csv_text)
