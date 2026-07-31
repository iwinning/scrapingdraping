from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


BUSINESS_DIRECTORY_DOMAINS = {
    "mrkoll.se",
    "www.mrkoll.se",
    "hitta.se",
    "www.hitta.se",
    "eniro.se",
    "www.eniro.se",
}

SENSITIVE_FIELD_HINTS = {
    "personnummer",
    "ssn",
    "social_security",
    "national_id",
    "passport",
    "bank",
    "credit_card",
    "health",
    "diagnosis",
    "religion",
    "politics",
    "protected_address",
}


@dataclass(slots=True)
class PolicyResult:
    allowed: bool
    message: str = ""


def validate_source_url(url: str, entity_type: str = "person") -> PolicyResult:
    if not url:
        return PolicyResult(True)

    parsed = urlparse(url)
    domain = parsed.netloc.lower().removeprefix("www.")
    if domain in {item.removeprefix("www.") for item in BUSINESS_DIRECTORY_DOMAINS} and entity_type != "company":
        return PolicyResult(
            False,
            "Directory URLs from Eniro, Hitta, and Mrkoll are allowed only for company records. Set entity_type=company for business listings.",
        )
    return PolicyResult(True)


def validate_headers(headers: list[str]) -> PolicyResult:
    lowered = {header.strip().lower() for header in headers}
    matched = sorted(lowered & SENSITIVE_FIELD_HINTS)
    if matched:
        return PolicyResult(
            False,
            f"CSV includes sensitive field(s): {', '.join(matched)}. Remove them before importing.",
        )
    return PolicyResult(True)
