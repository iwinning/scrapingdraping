from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .models import PersonRecord
from .policy import BUSINESS_DIRECTORY_DOMAINS


FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v2/search"
FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v2/scrape"
MAX_DETAIL_EXTRACTION_RECORDS = 10


COMPANY_DETAIL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "company_name": {"type": "string"},
        "phone": {"type": "string"},
        "email": {"type": "string"},
        "website": {"type": "string"},
        "address": {"type": "string"},
        "zip_code": {"type": "string"},
        "city": {"type": "string"},
        "country": {"type": "string"},
        "industry": {"type": "string"},
        "description": {"type": "string"},
    },
}


@dataclass(slots=True)
class FirecrawlSearchResult:
    title: str
    url: str
    description: str = ""

    def to_company_record(self, source: str = "Firecrawl") -> PersonRecord:
        domain = urlparse(self.url).netloc.removeprefix("www.")
        return PersonRecord.from_mapping(
            {
                "entity_type": "company",
                "name": self.title or domain or self.url,
                "profile_url": self.url,
                "source": f"{source}: {domain}" if domain else source,
                "notes": self.description,
                "tags": "firecrawl,company",
            }
        )


def search_firecrawl(
    query: str,
    *,
    limit: int = 10,
    include_domains: list[str] | None = None,
    api_key: str | None = None,
) -> list[FirecrawlSearchResult]:
    key = api_key or os.environ.get("FIRECRAWL_API_KEY")
    if not key:
        raise ValueError("Missing FIRECRAWL_API_KEY. Set it before using Firecrawl search.")
    if not query.strip():
        raise ValueError("Query is required.")

    payload: dict[str, Any] = {
        "query": query,
        "limit": max(1, min(int(limit), 25)),
        "sources": ["web"],
    }
    if include_domains:
        payload["includeDomains"] = [domain.strip().removeprefix("www.") for domain in include_domains if domain.strip()]

    request = Request(
        FIRECRAWL_SEARCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Firecrawl request failed with HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Firecrawl request failed: {exc.reason}") from exc

    parsed = json.loads(body)
    items = _extract_search_items(parsed)
    return [
        FirecrawlSearchResult(
            title=str(item.get("title") or "").strip(),
            url=str(item.get("url") or "").strip(),
            description=str(item.get("description") or item.get("markdown") or "").strip(),
        )
        for item in items
        if item.get("url")
    ]


def scrape_company_details(
    record: PersonRecord,
    *,
    api_key: str | None = None,
    wait_for_ms: int = 1000,
) -> PersonRecord:
    key = api_key or os.environ.get("FIRECRAWL_API_KEY")
    if not key:
        raise ValueError("Missing FIRECRAWL_API_KEY. Set it before using Firecrawl extraction.")
    if record.entity_type != "company":
        raise ValueError("Firecrawl detail extraction is company-only in this starter.")
    if not record.profile_url.strip():
        raise ValueError("Cannot extract details without a profile_url.")

    payload: dict[str, Any] = {
        "url": record.profile_url,
        "formats": [
            "links",
            "images",
            {
                "type": "json",
                "schema": COMPANY_DETAIL_SCHEMA,
                "prompt": (
                    "Extract only company/business listing information from this page. "
                    "Do not extract private-person information. Return empty strings when a field is missing."
                ),
            },
        ],
        "onlyMainContent": True,
        "removeBase64Images": True,
        "blockAds": True,
        "waitFor": max(0, min(int(wait_for_ms), 10000)),
        "timeout": 120000,
    }

    response = _post_firecrawl(FIRECRAWL_SCRAPE_URL, payload, key)
    data = response.get("data", response)
    extracted = data.get("json") or data.get("extract") or {}
    if not isinstance(extracted, dict):
        extracted = {}

    enriched = PersonRecord.from_mapping(record.as_dict())
    _fill_if_present(enriched, "name", extracted.get("company_name"))
    _fill_if_present(enriched, "phone", extracted.get("phone"))
    _fill_if_present(enriched, "email", extracted.get("email"))
    _fill_if_present(enriched, "website", extracted.get("website"))
    _fill_if_present(enriched, "address", extracted.get("address"))
    _fill_if_present(enriched, "zip_code", extracted.get("zip_code"))
    _fill_if_present(enriched, "city", extracted.get("city"))
    _fill_if_present(enriched, "country", extracted.get("country"))
    _fill_if_present(enriched, "organization", extracted.get("industry"))

    description = str(extracted.get("description") or "").strip()
    images = _normalize_assets(data.get("images"))[:10]
    links = _normalize_assets(data.get("links"))[:10]
    notes = [item for item in [record.notes.strip(), description] if item]
    if images:
        notes.append("Images: " + ", ".join(images))
    if links:
        notes.append("Links: " + ", ".join(links))
    enriched.notes = "\n".join(dict.fromkeys(notes))
    enriched.tags = ",".join(dict.fromkeys([tag for tag in [*record.tags.split(","), "firecrawl-detail"] if tag.strip()]))
    enriched.consent_basis = enriched.consent_basis or "company/public web extraction"
    return enriched


def validate_firecrawl_import(entity_type: str, include_domains: list[str]) -> None:
    normalized_domains = {domain.strip().lower().removeprefix("www.") for domain in include_domains}
    directory_domains = {domain.removeprefix("www.") for domain in BUSINESS_DIRECTORY_DOMAINS}
    if normalized_domains & directory_domains and entity_type != "company":
        raise ValueError("Firecrawl imports from Eniro, Hitta, or Mrkoll must use --entity-type company.")


def _post_firecrawl(url: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=130) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Firecrawl request failed with HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Firecrawl request failed: {exc.reason}") from exc
    return json.loads(body)


def _fill_if_present(record: PersonRecord, field: str, value: Any) -> None:
    clean = str(value or "").strip()
    if clean:
        setattr(record, field, clean)


def _normalize_assets(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    assets: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            assets.append(item.strip())
        elif isinstance(item, dict):
            url = str(item.get("url") or item.get("src") or item.get("href") or "").strip()
            if url:
                assets.append(url)
    return assets


def _extract_search_items(response: dict[str, Any]) -> list[dict[str, Any]]:
    data = response.get("data", response)
    if isinstance(data, dict):
        web_results = data.get("web")
        if isinstance(web_results, list):
            return [item for item in web_results if isinstance(item, dict)]
        search_results = data.get("results")
        if isinstance(search_results, list):
            return [item for item in search_results if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []
