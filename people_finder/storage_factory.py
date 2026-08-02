from __future__ import annotations

import os

from .storage import PeopleStore
from .supabase_storage import SupabasePeopleStore


# Bra kod: väljer backend enbart baserat på om Supabase-miljövariablerna finns satta,
# så samma kod funkar för lokal SQLite-utveckling och molndrift utan någon flagga att
# komma ihåg att sätta.
def make_store(db_path: str = "data/people.db"):
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        return SupabasePeopleStore()
    return PeopleStore(db_path)
