from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


# 1 — klart
# BEHÅLL — företag-only: domäner för svenska personsöktjänster, används för att
# begränsa scraping från dem till entity_type="company" (se validate_source_url nedan).
BUSINESS_DIRECTORY_DOMAINS = {
    "mrkoll.se",
    "www.mrkoll.se",
    "hitta.se",
    "www.hitta.se",
    "eniro.se",
    "www.eniro.se",
}

# 2 — klar 
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


# 3 — rätt, rör inte
@dataclass(slots=True)
class PolicyResult:
    allowed: bool
    message: str = ""


# 4 — rätt, rör inte (själva funktionssignaturen och tidig-return för tom url)
def validate_source_url(url: str, entity_type: str = "person") -> PolicyResult:
    if not url:
        return PolicyResult(True)

    parsed = urlparse(url)
    domain = parsed.netloc.lower().removeprefix("www.")


    #FLagga kan ändra detta om något inte funkar

     #Rad 45 är den som bestämmer att den inte kommer scrapa person data och bara företagsdata"
    # BEHÅLL — företag-only: raderna nedan är den faktiska spärren som blockerar
    # person-scraping från Eniro/Hitta/Mrkoll. OBS: just nu är blocket utkommenterat
    # (inuti en """-sträng) så spärren är INAKTIV i praktiken — funktionen returnerar
    # None istället för en PolicyResult. Låt den vara markerad så den inte tas bort av misstag.
    if domain in {item.removeprefix("www.") for item in BUSINESS_DIRECTORY_DOMAINS} and entity_type != "person":
        return PolicyResult(
            False,
            "Directory URLs from Eniro, Hitta, and Mrkoll are allowed only for person records. Set entity_type=person for private listings.",
        )
    return PolicyResult(True)


# 5 — rätt, rör inte (hela funktionen)
def validate_headers(headers: list[str]) -> PolicyResult:
    lowered = {header.strip().lower() for header in headers}
    matched = sorted(lowered & SENSITIVE_FIELD_HINTS)
    if matched:
        return PolicyResult(
            False,
            f"CSV includes sensitive field(s): {', '.join(matched)}. Remove them before importing.",
        )
    return PolicyResult(True)
