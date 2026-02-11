"""
Seed the SQLite database from the enriched CSV file.
Creates a default list called "All TX Non-QM Brokers" with all leads.
"""

import csv
import sqlite3
import os
import config
from models import init_db

INPUT_CSV = "TX-NON-Qm-Lending-Brokers-Final.csv"

# Mapping from CSV column header to DB column name
COLUMN_MAP = {
    "NMLSID": "nmlsid",
    "Name": "name",
    "LO Role": "lo_role",
    "Company NMLS": "company_nmls",
    "Company": "company",
    "Type": "type",
    "City": "city",
    "State": "state",
    "Office Type": "office_type",
    "Company Details": "company_details",
    "#": "rank",
    "Volume": "volume",
    "Units": "units",
    "Monthly Volume": "monthly_volume",
    "Monthly Units": "monthly_units",
    "Purchase Percent": "purchase_percent",
    "Monthly Volume Export": "monthly_volume_export",
    "Volume Export": "volume_export",
    "Company Website": "company_website",
    "Email": "email",
    "Facebook": "facebook",
    "LinkedIn": "linkedin",
    "Instagram": "instagram",
    "Twitter/X": "twitter_x",
    "YouTube": "youtube",
    "TikTok": "tiktok",
}


def import_csv(csv_path=INPUT_CSV):
    init_db()

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    # Build index mapping: CSV column index -> DB column name
    col_indices = {}
    for csv_col, db_col in COLUMN_MAP.items():
        if csv_col in header:
            col_indices[header.index(csv_col)] = db_col

    conn = sqlite3.connect(config.DATABASE)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    sorted_indices = sorted(col_indices.keys())
    db_columns = [col_indices[idx] for idx in sorted_indices]
    placeholders = ", ".join(["?"] * len(db_columns))
    col_names = ", ".join(db_columns)

    # Upsert: insert or update existing by nmlsid
    update_cols = [c for c in db_columns if c != "nmlsid"]
    update_set = ", ".join(f"{c} = excluded.{c}" for c in update_cols)

    insert_sql = f"""
        INSERT INTO leads ({col_names})
        VALUES ({placeholders})
        ON CONFLICT(nmlsid) DO UPDATE SET {update_set}
    """

    lead_count = 0
    lead_ids = []

    for row in rows:
        values = []
        for idx in sorted(col_indices.keys()):
            val = row[idx] if idx < len(row) else ""
            values.append(val)

        try:
            cur = conn.execute(insert_sql, values)
            # Get the lead id
            nmlsid_val = row[header.index("NMLSID")] if "NMLSID" in header else ""
            cur2 = conn.execute("SELECT id FROM leads WHERE nmlsid = ?", (nmlsid_val,))
            lead_row = cur2.fetchone()
            if lead_row:
                lead_ids.append(lead_row[0])
            lead_count += 1
        except Exception as e:
            print(f"  Error importing row: {e}")

    # Create default list
    conn.execute(
        "INSERT OR IGNORE INTO lists (name, filename, row_count, enrichment_status) VALUES (?, ?, ?, ?)",
        ("All TX Non-QM Brokers", csv_path, lead_count, "complete"),
    )
    list_row = conn.execute("SELECT id FROM lists WHERE name = ?", ("All TX Non-QM Brokers",)).fetchone()
    list_id = list_row[0]

    # Link all leads to this list
    for lead_id in lead_ids:
        conn.execute(
            "INSERT OR IGNORE INTO list_leads (list_id, lead_id) VALUES (?, ?)",
            (list_id, lead_id),
        )

    conn.commit()

    # Seed default message templates if none exist
    tpl_count = conn.execute("SELECT COUNT(*) FROM message_templates").fetchone()[0]
    if tpl_count == 0:
        seed_templates(conn)

    conn.close()

    print(f"Imported {lead_count} leads into database")
    print(f"Created list 'All TX Non-QM Brokers' with {len(lead_ids)} leads")
    return lead_count


def seed_templates(conn):
    """Insert default outreach message templates."""
    templates = [
        # Instagram
        ('The Compliment Opener', 'instagram',
         'Hey {name}! I came across {company} and saw you guys are crushing it with Non-QM in {city}. Love what you all are building. I work with a lender that has some of the most competitive Non-QM programs in TX — would love to connect and see if we can add value to what you are already doing.'),
        ('The Volume Flex', 'instagram',
         'Hey {name}, your production at {company} caught my eye — ranked #{rank} in TX Non-QM is no joke. I help brokers like you close more Non-QM deals with faster turns and better pricing. Worth a quick chat?'),
        ('The Casual Intro', 'instagram',
         'Hey {name}! Fellow mortgage person here. I saw {company} is doing big things in {city} and wanted to introduce myself. I work with a Non-QM lender that brokers keep telling me is their go-to. Would love to show you why — mind if I send over some details?'),
        ('The Value-First Hook', 'instagram',
         'Hey {name}, quick question — are you happy with your current Non-QM turn times? I ask because I work with brokers in {city} who went from 30-day closes to under 21. If {company} is looking for an edge, I would love to share what is working.'),
        ('The FOMO Play', 'instagram',
         'Hey {name}! A lot of top Non-QM brokers in TX are switching to us for better pricing and overlays. Seeing {company} ranked #{rank} in the state — figured you should at least know what is out there. Happy to send a rate sheet if you are open to it.'),
        ('The Short & Direct', 'instagram',
         'Hey {name}! Saw {company} is doing great Non-QM volume in {city}. I have a lender with aggressive pricing and same-day locks — worth a quick look? Happy to send details.'),
        ('The Curiosity Gap', 'instagram',
         'Hey {name}, I have been reaching out to the top Non-QM producers in TX and {company} kept coming up. There is one thing top brokers are doing differently right now to win more deals — mind if I share?'),
        ('The Warm Referral Feel', 'instagram',
         'Hey {name}! I have been connecting with a lot of Non-QM brokers in the {city} area and your name keeps coming up as someone doing serious volume at {company}. Would love to intro myself and see if there is a fit to work together.'),
        # LinkedIn
        ('The Professional Intro', 'linkedin',
         'Hi {name}, I came across your profile and saw the impressive Non-QM volume {company} is doing in {city}. I work with a wholesale lender specializing in Non-QM and would love to connect — always great to network with top producers in the space.'),
        ('The Mutual Value Prop', 'linkedin',
         'Hi {name}, I noticed {company} is ranked #{rank} in TX for Non-QM production — that is outstanding. I help brokers maximize their Non-QM pipeline with competitive pricing, flexible guidelines, and fast closes. Would love to explore if there is a fit to work together.'),
        ('The Industry Insider', 'linkedin',
         'Hi {name}, as someone working closely with Non-QM brokers across Texas, I have seen the market shift significantly this year. {company} clearly has strong positioning in {city}. I would love to connect and share some trends I am seeing that could help you capture even more volume.'),
        ('The Consultative Approach', 'linkedin',
         'Hi {name}, I have been researching the top Non-QM originators in TX and {company} stood out. Curious — what is your biggest challenge right now with Non-QM deals? I work on the wholesale side and often help brokers solve issues around pricing, overlays, or turn times.'),
        ('The Quick Pitch', 'linkedin',
         'Hi {name}, quick intro — I am an AE with a Non-QM wholesale lender and wanted to connect. We are helping brokers in {city} close more deals with same-day locks, minimal overlays, and dedicated support. Would love to show you what we offer at {company} level volume.'),
        ('The Thought Leader', 'linkedin',
         'Hi {name}, I have been following the Non-QM space closely and the growth from shops like {company} in {city} is exactly what the market needs. I work with a lender that is built to support high-volume producers like yourself — would love to connect and trade notes on where the market is heading.'),
        ('The Data-Driven Opener', 'linkedin',
         'Hi {name}, I pull Non-QM production data regularly and {company} at #{rank} in TX caught my attention — {volume} is serious volume. I partner with brokers at your level to help them get better execution on their Non-QM deals. Worth a conversation?'),
        ('The Warm Connection', 'linkedin',
         'Hi {name}, I have been connecting with several Non-QM brokers in the {city} market and your name came up as a top producer at {company}. Would love to add you to my network — I think there could be some real value in connecting.'),
        # Facebook
        ('The Friendly Intro', 'facebook',
         'Hey {name}! Hope you do not mind the message — I saw {company} is doing big things in the Non-QM space in {city} and had to reach out. I work with a wholesale lender that brokers keep telling me makes Non-QM easy. Would love to connect and see if we can help!'),
        ('The Local Angle', 'facebook',
         'Hey {name}! I have been connecting with a lot of mortgage pros in the {city} area and {company} keeps coming up. You all are clearly doing something right with Non-QM. I work on the wholesale side and would love to introduce myself — always looking to build relationships with top shops.'),
        ('The Casual Volume Mention', 'facebook',
         'Hey {name}, just wanted to say — {volume} in Non-QM volume at {company} is impressive. I work with a lender that is helping brokers like you close even more with better pricing and overlays. Figured it was worth reaching out. Open to chatting?'),
        ('The Problem Solver', 'facebook',
         'Hey {name}! Quick question — what is the biggest headache you deal with on Non-QM files right now? I ask because I work with brokers in {city} who used to have the same issues until they started working with us. Would love to see if we can help {company} too.'),
        ('The Social Proof Play', 'facebook',
         'Hey {name}! A bunch of top Non-QM brokers in TX have been switching to our lender lately — better pricing, faster turns, less hassle. Saw {company} is ranked #{rank} and figured you should at least have us in your back pocket. Worth a look?'),
        ('The No-Pressure Intro', 'facebook',
         'Hey {name}, not trying to sell you anything — just wanted to introduce myself. I am an AE working with a Non-QM wholesale lender and I have been reaching out to the top producers in TX. {company} doing {volume} in {city} definitely qualifies. Let me know if you ever want to compare notes.'),
        ('The Collaboration Angle', 'facebook',
         'Hey {name}! I have been working with some of the top Non-QM shops in Texas and love connecting with people who are really in the trenches. {company} is clearly doing well in {city} — would love to swap ideas and see if there is a way we can help each other win more deals.'),
        ('The Rate Teaser', 'facebook',
         'Hey {name}! Just curious — when is the last time you shopped your Non-QM rates? I work with a lender that has been beating the competition consistently and a lot of brokers in {city} have been making the switch. Happy to send {company} a rate sheet if you are open to it.'),
    ]

    for name, platform, content in templates:
        conn.execute(
            "INSERT INTO message_templates (name, platform, content) VALUES (?, ?, ?)",
            (name, platform, content),
        )
    conn.commit()
    print(f"Seeded {len(templates)} message templates")


if __name__ == "__main__":
    import_csv()
