from __future__ import annotations

from people_finder.server import PeopleFinderHandler
from people_finder.storage_factory import make_store


class handler(PeopleFinderHandler):
    store = make_store()
