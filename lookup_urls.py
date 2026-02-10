"""
Phase 1: Look up company website URLs for TX Non-QM lending brokers.

Uses DuckDuckGo search (free, no API key required).
Saves progress to a JSON cache so it can be resumed if interrupted.
"""

import csv
import json
import time
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from ddgs import DDGS

INPUT_CSV = "TX-NON-Qm-Lending-Brokers.csv"
OUTPUT_CSV = "TX-NON-Qm-Lending-Brokers-Enriched.csv"
CACHE_FILE = "url_cache.json"

# Delay between searches to avoid rate limiting
SEARCH_DELAY = 1.5  # seconds

# Domains to skip (these are aggregator/directory sites, not the company itself)
SKIP_DOMAINS = {
    "linkedin.com", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "youtube.com", "yelp.com", "bbb.org",
    "glassdoor.com", "indeed.com", "zillow.com", "realtor.com",
    "nmlsconsumeraccess.org", "mortgagemetrix.com", "wikipedia.org",
    "bloomberg.com", "crunchbase.com", "manta.com", "dnb.com",
    "buzzfile.com", "mapquest.com", "yellowpages.com",
    "companiesmarketcap.com", "zoominfo.com", "pitchbook.com",
    "sec.gov", "reddit.com", "tiktok.com",
}


def load_cache() -> dict:
    if Path(CACHE_FILE).exists():
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def is_valid_company_url(url: str) -> bool:
    """Filter out aggregator/directory sites."""
    try:
        domain = urlparse(url).netloc.lower()
        # Strip www.
        domain = re.sub(r"^www\.", "", domain)
        for skip in SKIP_DOMAINS:
            if domain == skip or domain.endswith("." + skip):
                return False
        return True
    except Exception:
        return False


def search_company_url(company_name: str) -> str:
    """Search DuckDuckGo for the company's official website."""
    query = f"{company_name} mortgage company official website"

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=8))

        for r in results:
            url = r.get("href", "")
            if is_valid_company_url(url):
                # Return just the base domain URL
                parsed = urlparse(url)
                return f"{parsed.scheme}://{parsed.netloc}"

        # If all results were filtered, return the first result anyway
        if results:
            url = results[0].get("href", "")
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"

    except Exception as e:
        print(f"  ERROR searching '{company_name}': {e}")

    return ""


def main():
    # Load existing cache
    cache = load_cache()
    print(f"Loaded cache with {len(cache)} entries")

    # Read input CSV
    with open(INPUT_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    # Get unique companies
    companies = sorted(set(row[4] for row in rows if len(row) > 4))
    remaining = [c for c in companies if c not in cache]

    print(f"Total unique companies: {len(companies)}")
    print(f"Already cached: {len(companies) - len(remaining)}")
    print(f"Remaining to look up: {len(remaining)}")
    print()

    # Look up remaining companies
    for i, company in enumerate(remaining, 1):
        print(f"[{i}/{len(remaining)}] Searching: {company}")
        url = search_company_url(company)
        cache[company] = url
        print(f"  -> {url or 'NOT FOUND'}")

        # Save cache every 10 lookups
        if i % 10 == 0:
            save_cache(cache)
            print(f"  (cache saved: {len(cache)} entries)")

        time.sleep(SEARCH_DELAY)

    # Final cache save
    save_cache(cache)
    print(f"\nAll lookups complete. Cache has {len(cache)} entries.")

    # Write enriched CSV
    new_header = header + ["Company Website"]
    enriched_rows = []
    for row in rows:
        company = row[4] if len(row) > 4 else ""
        website = cache.get(company, "")
        enriched_rows.append(row + [website])

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(new_header)
        writer.writerows(enriched_rows)

    print(f"Enriched CSV written to: {OUTPUT_CSV}")

    # Stats
    found = sum(1 for c in companies if cache.get(c))
    print(f"URLs found: {found}/{len(companies)} ({found*100//len(companies)}%)")


if __name__ == "__main__":
    main()
