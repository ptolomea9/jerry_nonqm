"""
Unified enrichment pipeline: URL lookup -> social scrape -> email scrape.
Runs as a background thread, updating DB records as it progresses.
"""

import sqlite3
import time
import config


def enrich_list(list_id):
    """Run the full enrichment pipeline for a list's leads."""
    conn = sqlite3.connect(config.DATABASE)
    conn.row_factory = sqlite3.Row

    try:
        # Get leads in this list that need enrichment
        leads = conn.execute(
            """SELECT l.id, l.nmlsid, l.name, l.company, l.company_website
               FROM leads l
               JOIN list_leads ll ON l.id = ll.lead_id
               WHERE ll.list_id = ?""",
            (list_id,),
        ).fetchall()

        total = len(leads)
        if total == 0:
            conn.execute("UPDATE lists SET enrichment_status = 'complete' WHERE id = ?", (list_id,))
            conn.commit()
            return

        # Stage 1: URL lookup for leads without websites
        conn.execute("UPDATE lists SET enrichment_status = 'enriching_urls' WHERE id = ?", (list_id,))
        conn.commit()

        needs_url = [l for l in leads if not l["company_website"]]
        if needs_url:
            try:
                from lookup_urls import search_company_url, load_cache as load_url_cache, save_cache as save_url_cache

                url_cache = load_url_cache()
                for i, lead in enumerate(needs_url):
                    company = lead["company"] or lead["name"]
                    if company not in url_cache:
                        url = search_company_url(company)
                        url_cache[company] = url
                        time.sleep(1.5)
                    else:
                        url = url_cache[company]

                    if url:
                        conn.execute("UPDATE leads SET company_website = ? WHERE id = ?", (url, lead["id"]))

                    if (i + 1) % 10 == 0:
                        save_url_cache(url_cache)
                        conn.commit()

                save_url_cache(url_cache)
                conn.commit()
            except Exception as e:
                print(f"URL enrichment error: {e}")

        # Refresh leads data after URL enrichment
        leads = conn.execute(
            """SELECT l.id, l.nmlsid, l.name, l.company, l.company_website
               FROM leads l
               JOIN list_leads ll ON l.id = ll.lead_id
               WHERE ll.list_id = ?""",
            (list_id,),
        ).fetchall()

        # Stage 2: Social media scraping
        conn.execute("UPDATE lists SET enrichment_status = 'enriching_socials' WHERE id = ?", (list_id,))
        conn.commit()

        needs_socials = [l for l in leads if l["company_website"]]
        if needs_socials:
            try:
                from scrape_socials import scrape_website, load_cache as load_social_cache, save_cache as save_social_cache
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

                social_cache = load_social_cache()
                platform_keys = ["facebook", "linkedin", "instagram", "twitter", "youtube", "tiktok"]
                db_keys = ["facebook", "linkedin", "instagram", "twitter_x", "youtube", "tiktok"]

                for i, lead in enumerate(needs_socials):
                    url = lead["company_website"]
                    if url not in social_cache:
                        socials = scrape_website(url)
                        social_cache[url] = socials
                        time.sleep(1.0)
                    else:
                        socials = social_cache[url]

                    for pk, dk in zip(platform_keys, db_keys):
                        val = socials.get(pk, "")
                        if val:
                            conn.execute(f"UPDATE leads SET {dk} = ? WHERE id = ? AND ({dk} IS NULL OR {dk} = '')", (val, lead["id"]))

                    if (i + 1) % 10 == 0:
                        save_social_cache(social_cache)
                        conn.commit()

                save_social_cache(social_cache)
                conn.commit()
            except Exception as e:
                print(f"Social enrichment error: {e}")

        # Stage 3: Email scraping
        conn.execute("UPDATE lists SET enrichment_status = 'enriching_emails' WHERE id = ?", (list_id,))
        conn.commit()

        try:
            from scrape_emails import (
                scrape_emails_from_website, search_email_for_company,
                load_cache as load_email_cache, save_cache as save_email_cache,
            )
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            email_cache = load_email_cache()

            # Refresh leads for email stage
            leads = conn.execute(
                """SELECT l.id, l.name, l.company, l.company_website, l.email
                   FROM leads l
                   JOIN list_leads ll ON l.id = ll.lead_id
                   WHERE ll.list_id = ?""",
                (list_id,),
            ).fetchall()

            for i, lead in enumerate(leads):
                if lead["email"]:
                    continue

                website = lead["company_website"]
                company = lead["company"] or lead["name"]
                key = website if website else f"__no_website__{company}"

                if key not in email_cache:
                    if website:
                        emails = scrape_emails_from_website(website)
                    else:
                        emails = search_email_for_company(company)
                    email_cache[key] = emails
                    time.sleep(1.0)
                else:
                    emails = email_cache[key]

                if emails:
                    conn.execute("UPDATE leads SET email = ? WHERE id = ?", (emails[0], lead["id"]))

                if (i + 1) % 10 == 0:
                    save_email_cache(email_cache)
                    conn.commit()

            save_email_cache(email_cache)
            conn.commit()
        except Exception as e:
            print(f"Email enrichment error: {e}")

        # Mark complete
        conn.execute("UPDATE lists SET enrichment_status = 'complete' WHERE id = ?", (list_id,))
        conn.commit()

    except Exception as e:
        print(f"Pipeline error: {e}")
        conn.execute("UPDATE lists SET enrichment_status = 'error' WHERE id = ?", (list_id,))
        conn.commit()
    finally:
        conn.close()
