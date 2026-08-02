from __future__ import annotations

import json
import os
from typing import Iterable
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .models import PERSON_FIELDS, PersonRecord
from .policy import validate_source_url
from .storage import AddManySummary


SUPABASE_TABLE = "people"


class SupabasePeopleStore:
    def __init__(self, url: str | None = None, service_key: str | None = None) -> None:
        self.url = (url or os.environ.get("SUPABASE_URL") or "").rstrip("/")
        self.service_key = service_key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or ""
        if not self.url or not self.service_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for Supabase storage.")

    # VIKTIGT – BEHÅLL DENNA KONTROLL: samma anropspunkt som storage.py PeopleStore.add() —
    # kör person/företag-policyn på varje post som sparas i Supabase. Tas den bort sparas
    # poster i molndatabasen utan någon kontroll alls. (Samma OBS som i storage.py gäller:
    # policy.py:s regel är just nu omvänd/trasig, men själva anropet ska vara kvar.)
    def add(self, record: PersonRecord) -> int | str:
        policy = validate_source_url(record.profile_url, record.entity_type)
        if not policy.allowed:
            raise ValueError(policy.message)
        if not record.name.strip():
            raise ValueError("Name is required.")
        response = self._request(
            "POST",
            f"/rest/v1/{SUPABASE_TABLE}",
            [self._record_payload(record)],
            headers={"Prefer": "return=representation"},
        )
        return response[0].get("id") if isinstance(response, list) and response else ""

    def add_many(self, records: Iterable[PersonRecord]) -> int:
        return self.add_many_with_summary(records).imported

    def add_many_with_summary(self, records: Iterable[PersonRecord]) -> AddManySummary:
        summary = AddManySummary()
        seen_batch: set[tuple[str, ...]] = set()
        payloads: list[dict[str, str]] = []
        # VIKTIGT – BEHÅLL DENNA KONTROLL: samma sak som add() ovan, fast för bulk-import.
        for record in records:
            policy = validate_source_url(record.profile_url, record.entity_type)
            if not policy.allowed:
                raise ValueError(policy.message)
            if not record.name.strip():
                summary.skipped_empty += 1
                continue
            fingerprint = self._fingerprint(record)
            if fingerprint in seen_batch or self._exists(record):
                summary.skipped_duplicates += 1
                continue
            seen_batch.add(fingerprint)
            payloads.append(self._record_payload(record))
        if payloads:
            self._request("POST", f"/rest/v1/{SUPABASE_TABLE}", payloads)
        summary.imported = len(payloads)
        return summary

    def search(self, query: str = "", limit: int = 1000) -> list[PersonRecord]:
        limit = max(1, min(int(limit), 5000))
        params: dict[str, str | int] = {
            "select": "*",
            "order": "collected_at.desc,id.desc",
            "limit": limit,
        }
        if query.strip():
            needle = query.strip().replace("*", "")
            or_parts = [
                f"{field}.ilike.*{needle}*"
                for field in [
                    "name",
                    "entity_type",
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
            ]
            params["or"] = f"({','.join(or_parts)})"
        response = self._request("GET", f"/rest/v1/{SUPABASE_TABLE}?{urlencode(params, safe='(),.*')}")
        return [PersonRecord.from_mapping(item) for item in response]

    # osäker – bör granskas manuellt: entity_type används här som en del av
    # dubblettnyckeln, inte som en person/företag-spärr (se _fingerprint nedan också).
    def _exists(self, record: PersonRecord) -> bool:
        if record.profile_url.strip():
            params = urlencode({"select": "id", "profile_url": f"eq.{record.profile_url.strip()}", "limit": 1})
            if self._request("GET", f"/rest/v1/{SUPABASE_TABLE}?{params}"):
                return True
        params = urlencode(
            {
                "select": "id",
                "entity_type": f"eq.{record.entity_type.strip()}",
                "name": f"eq.{record.name.strip()}",
                "zip_code": f"eq.{record.zip_code.strip()}",
                "city": f"eq.{record.city.strip()}",
                "limit": 1,
            }
        )
        return bool(self._request("GET", f"/rest/v1/{SUPABASE_TABLE}?{params}"))

    def _request(self, method: str, path: str, payload: object | None = None, headers: dict[str, str] | None = None) -> object:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            self.url + path,
            data=body,
            method=method,
            headers={
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
                "Content-Type": "application/json",
                **(headers or {}),
            },
        )
        with urlopen(request, timeout=60) as response:
            text = response.read().decode("utf-8")
        return json.loads(text) if text else []

    # Bra kod: bygger payloaden från PERSON_FIELDS istället för att hårdkoda fältnamn,
    # så den hänger med automatiskt när fält (som "age") läggs till i models.py.
    def _record_payload(self, record: PersonRecord) -> dict[str, str]:
        return {field: str(getattr(record, field) or "") for field in [*PERSON_FIELDS, "collected_at"]}

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
