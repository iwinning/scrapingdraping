from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


BLOCKED_PRIVATE_DIRECTORY_DOMAINS = {
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


def validate_source_url(url: str) -> PolicyResult:
    if not url:
        return PolicyResult(True)

    parsed = urlparse(url)
    domain = parsed.netloc.lower().removeprefix("www.")
    if domain in {item.removeprefix("www.") for item in BLOCKED_PRIVATE_DIRECTORY_DOMAINS}:
        return PolicyResult(
            False,
            "This starter blocks private-person directory targets by default. Use consented/public-professional sources instead.",
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
