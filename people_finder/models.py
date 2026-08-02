from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime, timezone
from typing import Any


PERSON_FIELDS = [
    "entity_type",
    "name",
    "role",
    "organization",
    "address",
    "zip_code",
    "city",
    "age",
    "country",
    "email",
    "phone",
    "website",
    "profile_url",
    "source",
    "notes",
    "tags",
    "consent_basis",
]


# osäker – bör granskas manuellt: entity_type är fältet som hela systemet använder för att
# skilja person- från företagsposter, men själva default-värdet "person" här är bara ett
# skema-defaultvärde för den generiska kontakt-databasen (manuell/CSV-inmatning av egna,
# samtyckta kontakter) — det är INTE samma sak som spärrarna mot Eniro/Hitta/Mrkoll i
# policy.py/firecrawl_client.py. Bör granskas ihop med normalize_entity_type nedan.
@dataclass(slots=True)
class PersonRecord:
    name: str
    entity_type: str = "person"
    role: str = ""
    organization: str = ""
    address: str = ""
    zip_code: str = ""
    city: str = ""
    age: str = ""
    country: str = ""
    email: str = ""
    phone: str = ""
    website: str = ""
    profile_url: str = ""
    source: str = "manual"
    notes: str = ""
    tags: str = ""
    consent_basis: str = ""
    collected_at: str = ""
    id: int | str | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "PersonRecord":
        clean = {field.name: str(data.get(field.name, "") or "").strip() for field in fields(cls)}
        if clean.get("id"):
            clean["id"] = int(clean["id"]) if clean["id"].isdigit() else clean["id"]
        else:
            clean["id"] = None
        clean["entity_type"] = normalize_entity_type(clean.get("entity_type", "person"))
        if not clean["collected_at"]:
            clean["collected_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return cls(**clean)

    # Bra kod: bygger dict:en dynamiskt från dataclassens fields() istället för att
    # hårdkoda fältnamnen igen — nya fält (t.ex. "age") kräver ingen ändring här,
    # så den kan inte glömmas bort/hamna i otakt med PERSON_FIELDS/dataclassen.
    def as_dict(self) -> dict[str, Any]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


# osäker – bör granskas manuellt: detta är INTE en spärr som blockerar/tillåter data —
# den bara normaliserar fritext (t.ex. "företag", "bolag", "organization") till antingen
# "person" eller "company", och faller tillbaka på "person" om värdet inte känns igen.
# Den avgör alltså inte vad som får sparas, bara vilket av de två kanoniska värdena en
# post får. De faktiska spärrarna finns i policy.py/firecrawl_client.py.
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
