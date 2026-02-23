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

# Mapping for XLSX company-level broker files
XLSX_COLUMN_MAP = {
    "Company NMLS": "nmlsid",
    "Company Name": "company",
    "Address.City": "city",
    "Address.State": "state",
    "Brokered Non-QM Volume (Last 13 Months)": "volume",
    "Brokered Non-QM Units (Last 13 Months)": "units",
    "Total Brokered Volume (Last 13 Months)": "volume_export",
    "Wholesale Account Executive": "lo_role",
    "Wholesale Account Status": "type",
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

    # Seed default message templates (inserts only missing ones)
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
        # TikTok
        ('The Quick Hook', 'tiktok',
         'Hey {name}! Saw {company} is doing serious Non-QM volume in {city} — love it. I work with a wholesale lender that is helping TX brokers close faster with better pricing. Would love to connect and see if there is a fit.'),
        ('The Casual DM', 'tiktok',
         'Hey {name}! Fellow mortgage person here. {company} caught my attention — ranked #{rank} for Non-QM in TX is impressive. I help brokers like you get better execution on Non-QM deals. Mind if I send over some details?'),
        ('The Trend Angle', 'tiktok',
         'Hey {name}, Non-QM is blowing up right now and {company} is clearly ahead of the curve in {city}. I work with a lender that is built for shops doing your kind of volume — same-day locks, minimal overlays. Worth a quick chat?'),
        ('The Short Pitch', 'tiktok',
         'Hey {name}! Quick intro — I am an AE with a Non-QM lender. We have been helping brokers in {city} close more deals with faster turns. Seeing what {company} is doing at #{rank} in TX, figured I should reach out. Open to connecting?'),
        ('The Social Proof', 'tiktok',
         'Hey {name}! A bunch of top Non-QM shops in TX have been switching to us lately. With {company} doing {volume} in {city}, you should at least see what we offer. Happy to send a rate sheet if you are interested.'),
        ('The Curiosity Hook', 'tiktok',
         'Hey {name}, there is one thing the top Non-QM brokers in TX are doing differently right now to win more deals. {company} is already crushing it at #{rank} — mind if I share what I am seeing?'),
        ('The Value Prop', 'tiktok',
         'Hey {name}! I have been connecting with Non-QM producers across TX and {company} keeps standing out. I work with a lender that specializes in making Non-QM easy — better pricing, faster turns, less hassle. Worth exploring?'),
        ('The Direct Approach', 'tiktok',
         'Hey {name}, not going to waste your time — I am an AE with a Non-QM wholesale lender. We are helping brokers in {city} get better rates and close in under 21 days. {company} doing {volume} tells me you could benefit. Want to take a look?'),
        # Email
        ('The Professional Introduction', 'email',
         'Subject: Non-QM Partnership Opportunity for {company}\n\nHi {name},\n\nI came across {company} while researching the top Non-QM originators in Texas, and your production at #{rank} is impressive. I am an Account Executive with a wholesale lender that specializes in Non-QM, and I wanted to introduce myself.\n\nWe have been helping brokers in {city} and across TX close more deals with:\n- Same-day rate locks\n- Minimal overlays\n- Dedicated AE support\n- Competitive pricing on DSCR, Bank Statement, and Asset Depletion programs\n\nWould you be open to a quick 10-minute call this week to see if there is a fit?\n\nBest regards'),
        ('The Value-First Email', 'email',
         'Subject: Helping {city} Brokers Win More Non-QM Deals\n\nHi {name},\n\nI have been working with several Non-QM brokers in the {city} market, and a common theme keeps coming up — turn times and overlays are killing deals.\n\nI work with a wholesale lender that has solved both of those problems. Our average Non-QM close time is under 21 days, and we have fewer overlays than most of the competition.\n\nGiven that {company} is already doing {volume} in Non-QM volume, I think we could help you close even more. Would you be open to seeing a rate sheet?\n\nBest regards'),
        ('The Data-Driven Email', 'email',
         'Subject: {company} Ranked #{rank} in TX Non-QM — Let us Help You Grow\n\nHi {name},\n\nI regularly analyze Non-QM production data across Texas, and {company} at #{rank} caught my attention. That level of volume in {city} tells me you know this space well.\n\nI am reaching out because the brokers I work with at similar volume levels have been able to increase their Non-QM closings by 15-20% after partnering with us — primarily through better pricing and faster execution.\n\nWould it be worth a 10-minute conversation to see if we can add value to what you are already doing?\n\nBest regards'),
        ('The Problem-Solution Email', 'email',
         'Subject: Quick Question About Your Non-QM Pipeline\n\nHi {name},\n\nQuick question — what is the biggest challenge you face right now when closing Non-QM deals at {company}?\n\nI ask because I work with a wholesale lender and the brokers I partner with in {city} used to struggle with the same things — slow turn times, surprise overlays, and inconsistent underwriting. We have built our entire process around eliminating those pain points.\n\nIf any of that resonates, I would love to share how we are helping shops like {company} close more deals with less friction.\n\nBest regards'),
        ('The Warm Outreach Email', 'email',
         'Subject: Connecting with Top Non-QM Producers in {city}\n\nHi {name},\n\nI have been reaching out to the top Non-QM producers in Texas to build relationships with the best in the business. {company} doing {volume} in {city} definitely qualifies.\n\nI am an AE with a Non-QM wholesale lender, and I am not here to hard sell — I genuinely believe that when great brokers partner with great lenders, everyone wins.\n\nWould you be open to a quick intro call? Even if the timing is not right now, I would love to have {company} in my network.\n\nBest regards'),
        ('The Rate Comparison Email', 'email',
         'Subject: Non-QM Rate Check for {company}\n\nHi {name},\n\nWhen was the last time you compared your Non-QM rates? I have been hearing from brokers in {city} that pricing has gotten increasingly competitive, and many are finding 25-50 bps in savings by shopping around.\n\nI work with a wholesale lender that has consistently been at the top of rate comparisons for DSCR, Bank Statement, and Asset Depletion programs. Given {company} is doing {volume} in volume, even a small pricing improvement could have a significant impact on your bottom line.\n\nHappy to send over a rate sheet — no strings attached. Would that be helpful?\n\nBest regards'),
        ('The Referral-Style Email', 'email',
         'Subject: Your Name Keeps Coming Up\n\nHi {name},\n\nI have been connecting with several mortgage professionals in the {city} market, and your name at {company} keeps coming up as one of the top Non-QM producers in the area.\n\nI am an AE with a Non-QM wholesale lender, and I make it a point to know the best brokers in every market. I would love to introduce myself and learn more about what is working well for {company} — and share some of what I am seeing from the lender side.\n\nDo you have 10 minutes this week for a quick call?\n\nBest regards'),
        ('The Follow-Up Friendly Email', 'email',
         'Subject: Non-QM Resources for {company}\n\nHi {name},\n\nI know your inbox is probably full, so I will keep this short. I am an AE with a Non-QM wholesale lender and I wanted to share a few resources that brokers in {city} have found valuable:\n\n- Our latest Non-QM rate sheet\n- A quick-reference guide for DSCR and Bank Statement qualification\n- Our scenario desk for tricky deals\n\nWith {company} ranked #{rank} in TX, I figured these might be useful. Happy to send any or all of them over — just let me know.\n\nBest regards'),
    ]

    count = 0
    for name, platform, content in templates:
        existing = conn.execute(
            "SELECT id FROM message_templates WHERE name = ? AND platform = ?",
            (name, platform),
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO message_templates (name, platform, content) VALUES (?, ?, ?)",
                (name, platform, content),
            )
            count += 1
    conn.commit()
    print(f"Seeded {count} new message templates ({len(templates)} total defined)")


if __name__ == "__main__":
    import_csv()
