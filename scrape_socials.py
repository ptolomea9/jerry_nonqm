"""
Phase 2: Scrape company websites for social media handles.

Visits each company URL from the enriched CSV, parses the page HTML
for social media links (Facebook, LinkedIn, Instagram, X/Twitter, YouTube, TikTok),
and writes results to a final enriched CSV.

Saves progress to a JSON cache so it can be resumed if interrupted.
"""

import csv
import json
import re
import time
import sys
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

INPUT_CSV = "TX-NON-Qm-Lending-Brokers-Enriched.csv"
OUTPUT_CSV = "TX-NON-Qm-Lending-Brokers-Final.csv"
SOCIAL_CACHE_FILE = "social_cache.json"

REQUEST_TIMEOUT = 10  # seconds
SCRAPE_DELAY = 1.0  # seconds between requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Social media platform patterns
SOCIAL_PATTERNS = {
    "facebook": {
        "domains": ["facebook.com", "fb.com", "fb.me"],
        "regex": r"https?://(?:www\.)?(?:facebook\.com|fb\.com|fb\.me)/[^\s\"'<>]+",
    },
    "linkedin": {
        "domains": ["linkedin.com"],
        "regex": r"https?://(?:www\.)?linkedin\.com/(?:company|in)/[^\s\"'<>]+",
    },
    "instagram": {
        "domains": ["instagram.com"],
        "regex": r"https?://(?:www\.)?instagram\.com/[^\s\"'<>]+",
    },
    "twitter": {
        "domains": ["twitter.com", "x.com"],
        "regex": r"https?://(?:www\.)?(?:twitter\.com|x\.com)/[^\s\"'<>]+",
    },
    "youtube": {
        "domains": ["youtube.com", "youtu.be"],
        "regex": r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s\"'<>]+",
    },
    "tiktok": {
        "domains": ["tiktok.com"],
        "regex": r"https?://(?:www\.)?tiktok\.com/@[^\s\"'<>]+",
    },
}

# URLs to skip (generic sharing/login links, not actual company profiles)
SKIP_PATTERNS = [
    "facebook.com/sharer",
    "facebook.com/share",
    "facebook.com/dialog",
    "twitter.com/intent",
    "twitter.com/share",
    "linkedin.com/shareArticle",
    "linkedin.com/share",
    "instagram.com/accounts",
    "youtube.com/embed",
    "youtube.com/watch",
    "facebook.com/tr",  # tracking pixel
    "facebook.com/plugins",
]


def load_cache() -> dict:
    if Path(SOCIAL_CACHE_FILE).exists():
        with open(SOCIAL_CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict):
    with open(SOCIAL_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def clean_url(url: str) -> str:
    """Remove trailing slashes, query params, fragments for cleaner output."""
    url = url.rstrip("/")
    # Remove common tracking params but keep the path
    url = re.sub(r"[?#].*$", "", url)
    return url


def is_skip_url(url: str) -> bool:
    """Check if URL is a share/intent link rather than a real profile."""
    url_lower = url.lower()
    return any(skip in url_lower for skip in SKIP_PATTERNS)


def extract_socials_from_html(html: str, base_url: str) -> dict:
    """Extract social media URLs from page HTML."""
    results = {}

    soup = BeautifulSoup(html, "html.parser")

    # Method 1: Find all <a> tags with href
    all_links = set()
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        # Handle relative URLs
        if href.startswith("/"):
            href = urljoin(base_url, href)
        all_links.add(href)

    # Method 2: Also regex the raw HTML for social URLs that might be in
    # JavaScript, data attributes, etc.
    for platform, config in SOCIAL_PATTERNS.items():
        matches = re.findall(config["regex"], html, re.IGNORECASE)
        all_links.update(matches)

    # Now classify all collected links
    for link in all_links:
        if is_skip_url(link):
            continue

        link_lower = link.lower()
        for platform, config in SOCIAL_PATTERNS.items():
            if platform in results:
                continue  # Already found this platform
            for domain in config["domains"]:
                if domain in link_lower:
                    results[platform] = clean_url(link)
                    break

    return results


def scrape_website(url: str) -> dict:
    """Fetch a URL and extract social media links."""
    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            verify=False,  # Some mortgage sites have bad certs
        )
        resp.raise_for_status()
        return extract_socials_from_html(resp.text, url)
    except Exception as e:
        print(f"  ERROR: {e}")
        return {}


def main():
    # Suppress SSL warnings since we set verify=False
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    cache = load_cache()
    print(f"Loaded social cache with {len(cache)} entries")

    # Read enriched CSV
    with open(INPUT_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    # Get unique URLs to scrape (skip empty)
    url_col_idx = header.index("Company Website")
    unique_urls = sorted(set(
        row[url_col_idx] for row in rows
        if len(row) > url_col_idx and row[url_col_idx]
    ))

    remaining = [u for u in unique_urls if u not in cache]

    print(f"Total unique URLs: {len(unique_urls)}")
    print(f"Already cached: {len(unique_urls) - len(remaining)}")
    print(f"Remaining to scrape: {len(remaining)}")
    print()

    for i, url in enumerate(remaining, 1):
        print(f"[{i}/{len(remaining)}] Scraping: {url}")
        socials = scrape_website(url)
        cache[url] = socials

        if socials:
            for platform, link in socials.items():
                print(f"  {platform}: {link}")
        else:
            print("  (no social links found)")

        if i % 10 == 0:
            save_cache(cache)
            print(f"  (cache saved: {len(cache)} entries)")

        time.sleep(SCRAPE_DELAY)

    save_cache(cache)
    print(f"\nAll scraping complete. Cache has {len(cache)} entries.")

    # Write final CSV
    social_columns = ["Facebook", "LinkedIn", "Instagram", "Twitter/X", "YouTube", "TikTok"]
    platform_keys = ["facebook", "linkedin", "instagram", "twitter", "youtube", "tiktok"]

    new_header = header + social_columns
    final_rows = []
    for row in rows:
        website = row[url_col_idx] if len(row) > url_col_idx else ""
        socials = cache.get(website, {})
        social_values = [socials.get(key, "") for key in platform_keys]
        final_rows.append(row + social_values)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(new_header)
        writer.writerows(final_rows)

    print(f"Final CSV written to: {OUTPUT_CSV}")

    # Stats
    platforms_found = {key: 0 for key in platform_keys}
    any_social = 0
    for url in unique_urls:
        socials = cache.get(url, {})
        if socials:
            any_social += 1
        for key in platform_keys:
            if key in socials:
                platforms_found[key] += 1

    print(f"\nCompanies with at least one social: {any_social}/{len(unique_urls)}")
    for key in platform_keys:
        print(f"  {key}: {platforms_found[key]}")


if __name__ == "__main__":
    main()
