# People Finder

A privacy-first personal research tool for collecting people, company, and contact records from sources you are allowed to use, searching them locally, and exporting the results as CSV or PDF.

This project is designed for consented sources, your own notes, CSV imports, public professional profiles, company records, and datasets you have permission to process. Eniro, Hitta, and Mrkoll URLs can be stored for company records by setting `entity_type` to `company`; private-person directory records remain blocked by default.

## Features

- Local SQLite database
- Simple browser UI
- Command-line interface
- Add/search people and company records
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
python -m people_finder add --entity-type person --name "Ada Lovelace" --role "Researcher" --organization "Example Lab" --zip-code "111 22" --city "Stockholm" --source "manual" --notes "Met at event; consented to follow-up."
```

Add a company record from a directory URL, including postnummer/ort:

```powershell
python -m people_finder add --entity-type company --name "Example AB" --zip-code "111 22" --city "Stockholm" --profile-url "https://www.eniro.se/example/f%C3%B6retag" --source "Eniro"
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

Search with Firecrawl:

```powershell
$env:FIRECRAWL_API_KEY = "fc-YOUR-API-KEY"
python -m people_finder firecrawl-search --query "redovisningsbyrå Stockholm företag" --include-domain eniro.se --limit 10
python -m people_finder firecrawl-search --query "redovisningsbyrå Stockholm företag" --include-domain eniro.se --limit 10 --import-results
```

The Firecrawl connector is company-only in this starter. Use it for sources and domains where you have permission to search/import data.

You can also add the Firecrawl API key directly in the web UI. The key is stored in your browser's localStorage and is not committed to GitHub or saved in the SQLite database.

## CSV columns

The importer accepts these columns:

```text
entity_type, name, role, organization, zip_code, city, country, email, phone, profile_url, source, notes, tags, consent_basis
```

Extra columns are ignored. Missing columns are treated as blank.

## Source guidance

Use this for:

- Contacts who gave permission
- Your own manually collected notes
- Public professional or organizational pages where collection is allowed
- Small, respectful research tasks with clear purpose
- Company directory entries that you are allowed to collect or import

The app keeps source and consent/lawful-basis fields visible so exported CSV/PDF files remain easy to review later.

## GitHub / Codex connection notes

When you are ready to connect this repo here:

1. Push this local folder to your GitHub repository.
2. In Codex, open or create a task from that GitHub repo/branch.
3. Ask Codex to continue from the repo, add features, or create a PR.

If you want a hosted platform later, the natural next step is to turn this into a small web app with authentication, clearer source connectors, and audit logs.
