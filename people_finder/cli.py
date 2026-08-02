from __future__ import annotations

import argparse
import json
from pathlib import Path

from .exporters import export_csv_file, export_pdf_file
from .firecrawl_client import search_firecrawl, validate_firecrawl_import
from .importers import records_from_csv_file
from .models import PERSON_FIELDS, PersonRecord
from .server import run_server
from .storage import PeopleStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Privacy-first people finder with CSV/PDF exports.")
    parser.add_argument("--db", default="data/people.db", help="SQLite database path.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 18 — rätt, rör inte (serve/add/import-csv/search/export-subparsers nedan)
    serve = subparsers.add_parser("serve", help="Run the local web UI.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", default=8765, type=int)

    add = subparsers.add_parser("add", help="Add a person record.")
    # Bra kod: genererar --flaggorna från PERSON_FIELDS istället för att lista dem för
    # hand — ett nytt fält i models.py (som "age") får automatiskt en CLI-flagga utan att
    # den här filen behöver ändras.
    for field in PERSON_FIELDS:
        required = field == "name"
        add.add_argument(f"--{field.replace('_', '-')}", default="", required=required)

    import_csv = subparsers.add_parser("import-csv", help="Import records from a CSV file.")
    import_csv.add_argument("path")

    search = subparsers.add_parser("search", help="Search records.")
    search.add_argument("--query", default="")
    search.add_argument("--limit", default=100, type=int)
    search.add_argument("--json", action="store_true", help="Print JSON instead of a table.")

    export = subparsers.add_parser("export", help="Export records.")
    export.add_argument("--query", default="")
    export.add_argument("--format", choices=["csv", "pdf"], required=True)
    export.add_argument("--output", required=True)

    firecrawl = subparsers.add_parser("firecrawl-search", help="Search web results through Firecrawl and optionally import company records.")
    # 19 — rätt, rör inte
    firecrawl.add_argument("--query", required=True)
    firecrawl.add_argument("--limit", default=10, type=int)
    firecrawl.add_argument("--include-domain", action="append", default=[], help="Restrict results to a domain. Can be repeated.")
    # BEHÅLL — företag-only: choices=["company"] gör det omöjligt att köra firecrawl-search
    # med entity_type="person" via CLI:t.
    # OBS – DENNA KONTROLL GÖR MOTSATSEN JUST NU: choices=["person"] gör att --entity-type
    # bara accepterar "person" (default är också "person"), vilket tvingar varje
    # firecrawl-search-körning till personläge och gör det omöjligt att be om
    # entity_type=company via CLI:t. Ska vara choices=["company"], default="company".
    firecrawl.add_argument("--entity-type", choices=["person"], default="person", help="Firecrawl imports are currently person-only.")
    # 20 — rätt, rör inte
    firecrawl.add_argument("--import-results", action="store_true", help="Save results as company records instead of only previewing.")

    return parser


# 21 — rätt, rör inte (hela main()-funktionen är oberoende av person/företag-buggen)
def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    store = PeopleStore(args.db)

    if args.command == "serve":
        run_server(db_path=args.db, host=args.host, port=args.port)
        return

    if args.command == "add":
        payload = {field: getattr(args, field) for field in PERSON_FIELDS}
        try:
            record_id = store.add(PersonRecord.from_mapping(payload))
        except ValueError as exc:
            parser.exit(2, f"Error: {exc}\n")
        print(f"Added record #{record_id}")
        return

    if args.command == "import-csv":
        try:
            records = records_from_csv_file(args.path)
            count = store.add_many(records)
        except ValueError as exc:
            parser.exit(2, f"Error: {exc}\n")
        print(f"Imported {count} record(s)")
        return

    if args.command == "search":
        records = store.search(query=args.query, limit=args.limit)
        if args.json:
            print(json.dumps([record.as_dict() for record in records], ensure_ascii=False, indent=2))
            return
        if not records:
            print("No records found.")
            return
        for record in records:
            parts = [record.name, record.role, record.organization, record.city, record.country]
            print(" | ".join(part for part in parts if part))
        return

    if args.command == "export":
        records = store.search(query=args.query)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        if args.format == "csv":
            export_csv_file(records, output)
        else:
            export_pdf_file(records, output)
        print(f"Exported {len(records)} record(s) to {output}")
        return

    if args.command == "firecrawl-search":
        try:
            validate_firecrawl_import(args.entity_type, args.include_domain)
            results = search_firecrawl(args.query, limit=args.limit, include_domains=args.include_domain)
        except (RuntimeError, ValueError) as exc:
            parser.exit(2, f"Error: {exc}\n")
        records = [result.to_company_record() for result in results]
        if args.import_results:
            count = store.add_many(records)
            print(f"Imported {count} Firecrawl result(s).")
        else:
            for record in records:
                print(f"{record.name} | {record.profile_url}")
            print(f"Previewed {len(records)} result(s). Add --import-results to save them.")
        return

    parser.error("Unknown command.")
