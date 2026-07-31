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

    policy = validate_headers(list(reader.fieldnames))
    if not policy.allowed:
        raise ValueError(policy.message)

    records: list[PersonRecord] = []
    for row in reader:
        payload = {field: row.get(field, "") for field in PERSON_FIELDS}
        if payload["name"].strip():
            records.append(PersonRecord.from_mapping(payload))
    return records


def records_from_csv_file(path: str | Path) -> list[PersonRecord]:
    csv_text = Path(path).read_text(encoding="utf-8-sig")
    return records_from_csv_text(csv_text)
