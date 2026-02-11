# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Jerry Non-QM List App** — Flask web application for AE outreach to Texas Non-QM (Non-Qualified Mortgage) lending brokers. 500 loan officers ranked by origination volume, enriched with company websites, social media profiles, and email addresses.

## Tech Stack

- **Backend:** Flask 3.1 + raw sqlite3 + Jinja2 (app factory pattern)
- **Frontend:** Tailwind CSS (CDN) + vanilla JS — no build step, no npm, no SPA
- **Database:** SQLite at `data/jerry_outreach.db` (WAL mode, foreign keys enabled)
- **Deployment:** Railway (auto-deploys on push to `main`)
- **Remote:** https://github.com/ptolomea9/jerry_nonqm.git

## Running the App

```bash
python import_csv.py    # Seed database from enriched CSV + message templates
python app.py           # Start server at http://localhost:5000
```

On Railway, `app.py:create_app()` auto-seeds if the leads table is empty (first deploy).

## Architecture

### App Factory (`app.py`)

`create_app()` initializes the app: runs `init_db()` for schema/migrations, auto-seeds on empty DB, registers teardown, then registers 7 blueprints.

### Blueprints (7 routes modules)

| Blueprint | File | Key Routes |
|-----------|------|------------|
| dashboard | `routes/dashboard.py` | `/dashboard` (stats), `/dashboard/export` (CSV) |
| leads | `routes/leads.py` | `/leads` (filterable table, search, pagination at 25/page) |
| lists | `routes/lists.py` | `/lists` (index), `/lists/upload` (CSV import), `/lists/<id>/enrich` (trigger pipeline) |
| flyers | `routes/flyers.py` | `/flyers` (upload/preview/delete images) |
| templates | `routes/templates.py` | `/templates` (CRUD for message templates with merge fields) |
| outreach | `routes/outreach.py` | `/outreach/setup`, `/outreach/start`, `/outreach/session/<id>` |
| api | `routes/api.py` | `/api/outreach/log` (AJAX send/skip), `/api/outreach/back`, `/api/lists/<id>/status` (enrichment polling) |

### Database Layer (`models.py`)

- `get_db()` — request-scoped connection via Flask `g` object, `sqlite3.Row` factory
- `query_db()` — convenience SELECT helper with `one=True` option
- `init_db()` — creates 7 tables from `SCHEMA` string, runs column migrations
- Schema changes: add columns via `ALTER TABLE` in `init_db()`, guarded by `PRAGMA table_info` check

### Key Data Patterns

- **Leads** are uniquely keyed by `nmlsid`. CSV uploads use `ON CONFLICT(nmlsid) DO UPDATE` for upserts.
- **Lists ↔ Leads** is many-to-many via `list_leads` junction table.
- **Outreach sessions** store the lead queue as a JSON array of IDs in a TEXT column. `current_index` tracks position; the queue is never modified — only the index advances or retreats.
- **Enrichment status** on lists: `none` → `enriching_urls` → `enriching_socials` → `enriching_emails` → `complete` (or `error`).
- **Message templates** support merge fields: `{name}`, `{company}`, `{city}`, `{rank}`, `{volume}`. Rendered server-side on page load and client-side on AJAX lead advance.

### Outreach Session Flow

1. Setup page: AE picks list + flyer + platform + template
2. `/outreach/start` queries eligible leads (have platform URL + not yet contacted) → creates session with lead_queue JSON
3. Session page shows one lead at a time. "Open Profile" opens social URL in new tab.
4. Sent/Skip → AJAX POST to `/api/outreach/log` → inserts log, increments index, returns next lead JSON
5. Back → AJAX POST to `/api/outreach/back` → deletes last log, decrements index
6. Keyboard shortcuts: `S` = sent, `X` = skip, `O` = open profile, `M` = copy message, `C` = copy flyer, `B` = back
7. All DOM updates via vanilla JS in `static/js/outreach.js` (IIFE pattern)

### Enrichment Pipeline (`enrichment/pipeline.py`)

Background thread spawned from `/lists/<id>/enrich`. Three stages, each with JSON cache for resumability:

1. **URL lookup** — DuckDuckGo search for company website (`lookup_urls.py`, cache: `url_cache.json`)
2. **Social scraping** — crawl websites for social links (`scrape_socials.py`, cache: `social_cache.json`)
3. **Email scraping** — mailto links, contact page crawl, regex extraction (`scrape_emails.py`, cache: `email_cache.json`)

Frontend polls `/api/lists/<id>/status` every 5 seconds; reloads page on completion.

### Template Inheritance

`templates/base.html` — Tailwind CDN, indigo navbar, flash messages. All pages extend this. Template directories mirror blueprint names: `templates/leads/`, `templates/lists/`, `templates/outreach/`, etc. `{% block scripts %}` for page-specific JS.

## Data Pipeline (offline scripts)

Run order: `lookup_urls.py` → `scrape_socials.py` → `scrape_emails.py` → `import_csv.py`

| Script | Input | Output | Cache |
|--------|-------|--------|-------|
| `lookup_urls.py` | Raw CSV | `TX-NON-Qm-Lending-Brokers-Enriched.csv` | `url_cache.json` |
| `scrape_socials.py` | Enriched CSV | `TX-NON-Qm-Lending-Brokers-Final.csv` | `social_cache.json` |
| `scrape_emails.py` | Final CSV | Final CSV (updated in place) | `email_cache.json` |
| `import_csv.py` | Final CSV | SQLite DB + message templates | — |

`import_csv.py` also seeds 40 prefab message templates (8 Instagram, 8 LinkedIn, 8 Facebook, 8 TikTok, 8 Email). Seed is idempotent — only inserts templates not already present by name+platform.

## CSV Column Mapping

`COLUMN_MAP` in `import_csv.py` maps CSV headers → DB columns. Reused by `routes/lists.py` for uploads. Upload auto-detects enrichment status: if CSV has "Company Website" AND "Facebook" columns → `complete`, otherwise `none`.

## File Uploads

- Flyers: `uploads/flyers/` (images/PDFs, UUID-prefixed filenames)
- CSVs: `uploads/csv/` (UUID-prefixed)
- Config: `config.py` defines allowed extensions and 16MB size limit
