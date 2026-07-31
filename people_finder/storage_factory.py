from __future__ import annotations

import os

from .storage import PeopleStore
from .supabase_storage import SupabasePeopleStore


def make_store(db_path: str = "data/people.db"):
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        return SupabasePeopleStore()
    return PeopleStore(db_path)
