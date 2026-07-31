from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime, timezone
from typing import Any


PERSON_FIELDS = [
    "entity_type",
    "name",
    "role",
    "organization",
    "zip_code",
    "city",
    "country",
    "email",
    "phone",
    "profile_url",
    "source",
    "notes",
    "tags",
    "consent_basis",
]


@dataclass(slots=True)
class PersonRecord:
    name: str
    entity_type: str = "person"
    role: str = ""
    organization: str = ""
    zip_code: str = ""
    city: str = ""
    country: str = ""
    email: str = ""
    phone: str = ""
    profile_url: str = ""
    source: str = "manual"
    notes: str = ""
    tags: str = ""
    consent_basis: str = ""
    collected_at: str = ""
    id: int | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "PersonRecord":
        clean = {field.name: str(data.get(field.name, "") or "").strip() for field in fields(cls)}
        clean["id"] = int(clean["id"]) if clean.get("id") else None
        clean["entity_type"] = normalize_entity_type(clean.get("entity_type", "person"))
        if not clean["collected_at"]:
            clean["collected_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return cls(**clean)

    def as_dict(self) -> dict[str, Any]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


def normalize_entity_type(value: str) -> str:
    normalized = (value or "person").strip().lower()
    aliases = {
        "business": "company",
        "företag": "company",
        "bolag": "company",
        "organisation": "company",
        "organization": "company",
        "privatperson": "person",
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in {"person", "company"} else "person"
