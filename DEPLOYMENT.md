# Deployment: Vercel + Supabase

This repo can run locally with SQLite, or on Vercel with Supabase.

## How memory/data works

Local mode:

- Code lives in GitHub.
- Records are stored in `data/people.db`.
- Firecrawl API key can be stored in the browser for local use.

Vercel/Supabase mode:

- Code runs on Vercel as a Python Function.
- Records are stored in Supabase Postgres.
- Server-side secrets are stored as Vercel environment variables.
- The browser can still hold a Firecrawl key locally, but for production you can also set `FIRECRAWL_API_KEY` in Vercel.

## Supabase setup

1. Create a Supabase project.
2. Open the SQL Editor.
3. Run `supabase/schema.sql`.
4. Copy your project URL.
5. Copy your service role key. Keep this secret; do not expose it in frontend code.

## Vercel setup

1. Import the GitHub repo in Vercel.
2. Add these environment variables:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
FIRECRAWL_API_KEY
```

3. Deploy.

Vercel will route the app through `api/index.py`. If Supabase env vars are present, the app uses Supabase. If not, local runs use SQLite.

## Firecrawl flow

The app uses Firecrawl in two stages:

1. Search for company result URLs.
2. Extract details from selected company pages.

The detail extraction step asks Firecrawl for structured company fields:

- company name
- phone
- email
- website
- address
- postnummer / ZIP
- city
- country
- industry
- description
- links/images in notes

The app does not run an unlimited crawler. Keep search/detail extraction scoped with domains, city/postnummer, max results, and selected import.
