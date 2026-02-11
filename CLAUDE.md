# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Jerry Non-QM List App** — a Flask web application for AE outreach to Texas Non-QM (Non-Qualified Mortgage) lending brokers. The dataset ranks 500 loan officers and branch managers by origination volume, enriched with company websites, social media profiles, and email addresses.

## Tech Stack

- **Backend:** Flask 3.1 + raw sqlite3 + Jinja2
- **Frontend:** Tailwind CSS (CDN) + vanilla JS
- **Database:** SQLite at `data/jerry_outreach.db`
- **No build step, no npm, no SPA framework**

## Running the App

```bash
python import_csv.py    # Seed database from enriched CSV
python app.py           # Start server at http://localhost:5000
```

## Data Enrichment Pipeline

The data goes through 4 stages. Each script is resumable via JSON caches.

| Stage | Script | Input | Output | Cache |
|-------|--------|-------|--------|-------|
| Raw data | — | MortgageMetrix export | `TX-NON-Qm-Lending-Brokers.csv` | — |
| Phase 1: URLs | `lookup_urls.py` | Raw CSV | `TX-NON-Qm-Lending-Brokers-Enriched.csv` | `url_cache.json` |
| Phase 2: Socials | `scrape_socials.py` | Enriched CSV | `TX-NON-Qm-Lending-Brokers-Final.csv` | `social_cache.json` |
| Phase 2.5: Emails | `scrape_emails.py` | Final CSV | Final CSV (updated in place) | `email_cache.json` |

**Run order:** `lookup_urls.py` → `scrape_socials.py` → `scrape_emails.py` → `import_csv.py`

### Enrichment methods

**URL lookup** (`lookup_urls.py`): DuckDuckGo search for company official website. Filters aggregator/directory sites. 94% match rate.

**Social scraping** (`scrape_socials.py`): Visits each company website, extracts social links from `<a>` tags + regex on raw HTML. Platforms: Facebook, LinkedIn, Instagram, Twitter/X, YouTube, TikTok.

**Email scraping** (`scrape_emails.py`): Three methods per company website:
1. `mailto:` links in HTML (highest confidence)
2. Crawl `/contact`, `/contact-us`, `/about`, `/about-us` subpages
3. Regex email extraction from raw HTML (filtered against junk domains)
4. For companies with NO website: DuckDuckGo search fallback

### In-app enrichment

The web app has a built-in enrichment pipeline (`enrichment/pipeline.py`) that can be triggered from the Lists page. When an AE uploads a raw CSV without website/social columns, clicking "Enrich Data" runs all three stages as a background thread. The list detail page polls for progress updates every 5 seconds.

## Data

### CSV Files

| File | Description |
|------|-------------|
| `TX-NON-Qm-Lending-Brokers.csv` | Original MortgageMetrix export (500 rows, 18 columns) |
| `TX-NON-Qm-Lending-Brokers-Enriched.csv` | After Phase 1: +Company Website column |
| `TX-NON-Qm-Lending-Brokers-Final.csv` | After Phase 2 & 2.5: +Facebook, LinkedIn, Instagram, Twitter/X, YouTube, TikTok, Email |

### Database Schema (6 tables)

- **leads** — One row per NMLSID, all CSV columns + enrichment data
- **lists** — Uploaded CSV campaign segments
- **list_leads** — Many-to-many junction table
- **flyers** — Uploaded flyer images
- **outreach_sessions** — Batch: list + flyer + platform, lead queue as JSON
- **outreach_logs** — One row per send/skip action with timestamp

## Web App Pages

| Page | Route | Purpose |
|------|-------|---------|
| Dashboard | `/dashboard` | Stats, social coverage, recent activity, CSV export |
| Lead Browser | `/leads` | Filterable table with social badges (green=available, gray=missing) |
| Lists | `/lists` | Upload CSVs, view segments, trigger enrichment |
| Flyers | `/flyers` | Upload/preview/delete flyer images |
| Outreach Setup | `/outreach/setup` | Pick list + flyer + platform |
| Outreach Session | `/outreach/session/<id>` | One lead at a time: Open Profile → Sent/Skip → auto-advance |
| Session Summary | `/outreach/session/<id>/summary` | Completion stats |

### Outreach Workflow

1. AE selects list, flyer, and platform on setup page
2. App queries leads with that platform available + not yet contacted
3. Session page shows one lead at a time with progress bar
4. "Open Profile" opens social URL in new tab; AE sends DM manually
5. Thumbs up (sent) or thumbs down (skip) logs the action
6. AJAX advances to next lead without page reload
7. Keyboard shortcuts: `S` = sent, `X` = skip, `O` = open profile

## Repository

- **Remote:** https://github.com/ptolomea9/jerry_nonqm.git
- **Default branch:** main
