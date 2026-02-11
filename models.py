import sqlite3
import os
from flask import g
import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    filename TEXT,
    row_count INTEGER DEFAULT 0,
    enrichment_status TEXT DEFAULT 'none',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nmlsid TEXT UNIQUE NOT NULL,
    name TEXT,
    lo_role TEXT,
    company_nmls TEXT,
    company TEXT,
    type TEXT,
    city TEXT,
    state TEXT,
    office_type TEXT,
    company_details TEXT,
    rank INTEGER,
    volume TEXT,
    units INTEGER,
    monthly_volume TEXT,
    monthly_units INTEGER,
    purchase_percent TEXT,
    monthly_volume_export TEXT,
    volume_export TEXT,
    company_website TEXT,
    email TEXT,
    facebook TEXT,
    linkedin TEXT,
    instagram TEXT,
    twitter_x TEXT,
    youtube TEXT,
    tiktok TEXT
);

CREATE TABLE IF NOT EXISTS list_leads (
    list_id INTEGER NOT NULL,
    lead_id INTEGER NOT NULL,
    PRIMARY KEY (list_id, lead_id),
    FOREIGN KEY (list_id) REFERENCES lists(id),
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);

CREATE TABLE IF NOT EXISTS flyers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    file_type TEXT,
    tags TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outreach_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id INTEGER,
    flyer_id INTEGER,
    platform TEXT NOT NULL,
    lead_queue TEXT DEFAULT '[]',
    current_index INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (list_id) REFERENCES lists(id),
    FOREIGN KEY (flyer_id) REFERENCES flyers(id)
);

CREATE TABLE IF NOT EXISTS outreach_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    lead_id INTEGER NOT NULL,
    platform TEXT,
    flyer_id INTEGER,
    result TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES outreach_sessions(id),
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);
"""


def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(config.DATABASE), exist_ok=True)
        g.db = sqlite3.connect(config.DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(config.DATABASE), exist_ok=True)
    conn = sqlite3.connect(config.DATABASE)
    conn.executescript(SCHEMA)
    conn.close()


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv
