"""
Phase 2.5: Scrape company websites for email addresses.

Three extraction methods per company website:
1. mailto: links in HTML (highest confidence)
2. Crawl /contact or /about page if no mailto on homepage
3. Regex email extraction from raw HTML (filtered against junk domains)

For companies with NO website: DuckDuckGo search for email contact info.

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

INPUT_CSV = "TX-NON-Qm-Lending-Brokers-Final.csv"
OUTPUT_CSV = "TX-NON-Qm-Lending-Brokers-Final.csv"  # Update in place
EMAIL_CACHE_FILE = "email_cache.json"

REQUEST_TIMEOUT = 10  # seconds
SCRAPE_DELAY = 1.0  # seconds between requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Email regex: standard local@domain.tld pattern
EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# Junk domains to filter out (not real contact emails)
JUNK_DOMAINS = {
    "example.com", "example.org", "test.com", "localhost",
    "sentry.io", "wixpress.com", "wix.com",
    "googleapis.com", "googleusercontent.com", "google.com",
    "facebook.com", "twitter.com", "instagram.com",
    "wordpress.com", "wordpress.org", "wp.com",
    "gravatar.com", "schema.org", "w3.org",
    "apple.com", "microsoft.com", "outlook.com",
    "changedetection.io", "cloudflare.com",
    "bootstrapcdn.com", "jsdelivr.net", "cdnjs.cloudflare.com",
    "fontawesome.com", "gstatic.com",
    "yourdomain.com", "domain.com", "email.com",
    "company.com", "yourcompany.com", "sampledomain.com",
}

# Junk email prefixes (generic/noreply addresses to deprioritize)
JUNK_PREFIXES = {
    "noreply", "no-reply", "donotreply", "do-not-reply",
    "mailer-daemon", "postmaster", "webmaster",
    "admin", "administrator", "root", "support",
    "abuse", "spam", "security",
}

# Subpages to crawl if homepage has no emails
CONTACT_PATHS = ["/contact", "/contact-us", "/about", "/about-us"]


def load_cache() -> dict:
    if Path(EMAIL_CACHE_FILE).exists():
        with open(EMAIL_CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict):
    with open(EMAIL_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def is_junk_email(email: str) -> bool:
    """Check if an email is a junk/placeholder address."""
    email_lower = email.lower()
    local, _, domain = email_lower.partition("@")

    # Filter junk domains
    if domain in JUNK_DOMAINS:
        return True

    # Filter image/file extensions mistaken as emails
    if domain.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".css", ".js")):
        return True

    return False


def score_email(email: str) -> int:
    """Score an email for relevance. Higher = better."""
    local = email.lower().split("@")[0]

    # Deprioritize junk prefixes
    if local in JUNK_PREFIXES:
        return 1

    # Prefer common business contact patterns
    if local in ("info", "contact", "hello", "inquiries", "loans", "mortgage"):
        return 10

    # Named emails (likely a real person) are good
    if "." in local and len(local) > 5:
        return 8

    return 5


def fetch_page(url: str) -> str:
    """Fetch a URL and return its HTML text."""
    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            verify=False,
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return ""


def extract_emails_from_html(html: str) -> list:
    """Extract email addresses from HTML using multiple methods."""
    emails = set()

    soup = BeautifulSoup(html, "html.parser")

    # Method 1: mailto: links (highest confidence)
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.lower().startswith("mailto:"):
            raw = href[7:].split("?")[0].strip()
            if EMAIL_REGEX.match(raw):
                emails.add(raw.lower())

    # Method 2: Regex on raw HTML
    for match in EMAIL_REGEX.findall(html):
        emails.add(match.lower())

    # Filter junk
    valid = [e for e in emails if not is_junk_email(e)]
    return valid


def scrape_emails_from_website(url: str) -> list:
    """Scrape a company website for email addresses."""
    all_emails = []

    # Step 1: Scrape homepage
    html = fetch_page(url)
    if html:
        all_emails.extend(extract_emails_from_html(html))

    # Step 2: If no emails found, try contact/about pages
    if not all_emails and html:
        for path in CONTACT_PATHS:
            subpage_url = urljoin(url.rstrip("/") + "/", path.lstrip("/"))
            sub_html = fetch_page(subpage_url)
            if sub_html:
                all_emails.extend(extract_emails_from_html(sub_html))
            if all_emails:
                break
            time.sleep(0.5)

    # Deduplicate and sort by relevance
    unique = list(set(all_emails))
    unique.sort(key=score_email, reverse=True)
    return unique


def search_email_for_company(company_name: str) -> list:
    """DuckDuckGo search for company email when no website exists."""
    try:
        from ddgs import DDGS

        query = f'"{company_name}" mortgage email contact Texas'
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))

        emails = set()
        for r in results:
            body = r.get("body", "") + " " + r.get("title", "")
            for match in EMAIL_REGEX.findall(body):
                if not is_junk_email(match.lower()):
                    emails.add(match.lower())

        return list(emails)
    except Exception as e:
        print(f"  ERROR searching '{company_name}': {e}")
        return []


def main():
    # Suppress SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    cache = load_cache()
    print(f"Loaded email cache with {len(cache)} entries")

    # Read CSV
    with open(INPUT_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    url_col_idx = header.index("Company Website")
    company_col_idx = header.index("Company")

    # Build work list: unique (website_url, company_name) pairs
    seen = {}
    for row in rows:
        website = row[url_col_idx] if len(row) > url_col_idx else ""
        company = row[company_col_idx] if len(row) > company_col_idx else ""
        key = website if website else f"__no_website__{company}"
        if key not in seen:
            seen[key] = {"website": website, "company": company}

    remaining = {k: v for k, v in seen.items() if k not in cache}

    print(f"Total unique targets: {len(seen)}")
    print(f"Already cached: {len(seen) - len(remaining)}")
    print(f"Remaining to scrape: {len(remaining)}")
    print()

    for i, (key, info) in enumerate(remaining.items(), 1):
        website = info["website"]
        company = info["company"]

        if website:
            print(f"[{i}/{len(remaining)}] Scraping: {website}")
            emails = scrape_emails_from_website(website)
        else:
            print(f"[{i}/{len(remaining)}] Searching (no website): {company}")
            emails = search_email_for_company(company)

        cache[key] = emails

        if emails:
            for email in emails:
                print(f"  {email}")
        else:
            print("  (no emails found)")

        if i % 10 == 0:
            save_cache(cache)
            print(f"  (cache saved: {len(cache)} entries)")

        time.sleep(SCRAPE_DELAY)

    save_cache(cache)
    print(f"\nAll scraping complete. Cache has {len(cache)} entries.")

    # Update CSV with Email column
    # Check if Email column already exists
    if "Email" in header:
        email_col_idx = header.index("Email")
        new_header = header
    else:
        email_col_idx = None
        new_header = header + ["Email"]

    final_rows = []
    for row in rows:
        website = row[url_col_idx] if len(row) > url_col_idx else ""
        company = row[company_col_idx] if len(row) > company_col_idx else ""
        key = website if website else f"__no_website__{company}"
        emails = cache.get(key, [])
        best_email = emails[0] if emails else ""

        if email_col_idx is not None:
            row[email_col_idx] = best_email
            final_rows.append(row)
        else:
            final_rows.append(row + [best_email])

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(new_header)
        writer.writerows(final_rows)

    print(f"CSV updated: {OUTPUT_CSV}")

    # Stats
    total_with_email = sum(1 for k in seen if cache.get(k))
    print(f"\nTargets with at least one email: {total_with_email}/{len(seen)}")


if __name__ == "__main__":
    main()
