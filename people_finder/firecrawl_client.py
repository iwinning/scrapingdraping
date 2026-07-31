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


def validate_firecrawl_import(entity_type: str, include_domains: list[str]) -> None:
    normalized_domains = {domain.strip().lower().removeprefix("www.") for domain in include_domains}
    directory_domains = {domain.removeprefix("www.") for domain in BUSINESS_DIRECTORY_DOMAINS}
    if normalized_domains & directory_domains and entity_type != "company":
        raise ValueError("Firecrawl imports from Eniro, Hitta, or Mrkoll must use --entity-type company.")


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
