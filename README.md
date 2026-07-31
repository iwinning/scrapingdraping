# People Finder

A privacy-first personal research tool for collecting people/contact records from sources you are allowed to use, searching them locally, and exporting the results as CSV or PDF.

This project intentionally does **not** include scrapers for private-person directory sites such as Mrkoll, Hitta person search, or Eniro person listings. Those sites can involve personal data, terms-of-service limits, and GDPR/privacy risks. The starter app is designed for consented sources, your own notes, CSV imports, public professional profiles, and datasets you have permission to process.

## Features

- Local SQLite database
- Simple browser UI
- Command-line interface
- Add/search people records
- Import records from CSV
- Export filtered results as `.csv`
- Export filtered results as `.pdf`
- Built-in guardrails for high-risk private directory targets and sensitive fields

## Quick start

```powershell
python -m people_finder serve
```

Then open:

```text
http://127.0.0.1:8765
```

## CLI examples

Add a record:

```powershell
python -m people_finder add --name "Ada Lovelace" --role "Researcher" --organization "Example Lab" --city "Stockholm" --source "manual" --notes "Met at event; consented to follow-up."
```

Search:

```powershell
python -m people_finder search --query "Stockholm"
```

Import CSV:

```powershell
python -m people_finder import-csv .\contacts.csv
```

Export:

```powershell
python -m people_finder export --format csv --output .\people.csv
python -m people_finder export --format pdf --output .\people.pdf
```

## CSV columns

The importer accepts these columns:

```text
name, role, organization, city, ZIP ocde, country, email, phone, profile_url, source, notes, tags, consent_basis
```

Extra columns are ignored. Missing columns are treated as blank.

## Source guidance

Use this for:

- Contacts who gave permission
- Your own manually collected notes
- Public professional or organizational pages where collection is allowed
- Small, respectful research tasks with clear purpose
- Bulk scraping private individuals
- Collecting personal addresses





## GitHub / Codex connection notes

When you are ready to connect this repo here:

1. Push this local folder to your GitHub repository.
2. In Codex, open or create a task from that GitHub repo/branch.
3. Ask Codex to continue from the repo, add features, or create a PR.

If you want a hosted platform later, the natural next step is to turn this into a small web app with authentication, clearer source connectors, and audit logs.
