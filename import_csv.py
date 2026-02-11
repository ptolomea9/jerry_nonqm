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

    db_columns = list(col_indices.values())
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
    conn.close()

    print(f"Imported {lead_count} leads into database")
    print(f"Created list 'All TX Non-QM Brokers' with {len(lead_ids)} leads")
    return lead_count


if __name__ == "__main__":
    import_csv()
