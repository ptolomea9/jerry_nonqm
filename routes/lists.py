import csv
import os
import uuid
import threading
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
import config
from models import get_db, query_db

bp = Blueprint("lists", __name__)


@bp.route("/lists")
def index():
    lists = query_db("SELECT * FROM lists ORDER BY created_at DESC")
    return render_template("lists/index.html", lists=lists)


@bp.route("/lists/upload", methods=["POST"])
def upload():
    if "csv_file" not in request.files:
        flash("No file selected", "error")
        return redirect(url_for("lists.index"))

    file = request.files["csv_file"]
    if file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("lists.index"))

    if not file.filename.lower().endswith(".csv"):
        flash("Only CSV files are allowed", "error")
        return redirect(url_for("lists.index"))

    list_name = request.form.get("list_name", "").strip() or file.filename

    # Save file
    os.makedirs(config.UPLOAD_FOLDER_CSV, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{file.filename}"
    filepath = os.path.join(config.UPLOAD_FOLDER_CSV, stored_name)
    file.save(filepath)

    # Parse CSV and import leads
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
    except Exception as e:
        flash(f"Error reading CSV: {e}", "error")
        return redirect(url_for("lists.index"))

    db = get_db()

    # Determine if this CSV has enrichment columns
    has_website = "Company Website" in header
    has_socials = "Facebook" in header
    enrichment_status = "complete" if (has_website and has_socials) else "none"

    # Create list record
    cur = db.execute(
        "INSERT INTO lists (name, filename, row_count, enrichment_status) VALUES (?, ?, ?, ?)",
        (list_name, stored_name, len(rows), enrichment_status),
    )
    list_id = cur.lastrowid

    # Column mapping
    from import_csv import COLUMN_MAP

    col_indices = {}
    for csv_col, db_col in COLUMN_MAP.items():
        if csv_col in header:
            col_indices[header.index(csv_col)] = db_col

    db_columns = list(col_indices.values())
    placeholders = ", ".join(["?"] * len(db_columns))
    col_names = ", ".join(db_columns)
    update_cols = [c for c in db_columns if c != "nmlsid"]
    update_set = ", ".join(f"{c} = excluded.{c}" for c in update_cols)

    insert_sql = f"""
        INSERT INTO leads ({col_names})
        VALUES ({placeholders})
        ON CONFLICT(nmlsid) DO UPDATE SET {update_set}
    """

    nmlsid_idx = header.index("NMLSID") if "NMLSID" in header else None
    lead_ids = []

    for row in rows:
        values = []
        for idx in sorted(col_indices.keys()):
            val = row[idx] if idx < len(row) else ""
            values.append(val)

        try:
            db.execute(insert_sql, values)
            if nmlsid_idx is not None:
                nmlsid = row[nmlsid_idx]
                lead_row = db.execute("SELECT id FROM leads WHERE nmlsid = ?", (nmlsid,)).fetchone()
                if lead_row:
                    lead_ids.append(lead_row["id"])
        except Exception as e:
            print(f"  Error importing row: {e}")

    for lead_id in lead_ids:
        db.execute("INSERT OR IGNORE INTO list_leads (list_id, lead_id) VALUES (?, ?)", (list_id, lead_id))

    db.commit()
    flash(f"Imported {len(lead_ids)} leads into '{list_name}'", "success")
    return redirect(url_for("lists.detail", list_id=list_id))


@bp.route("/lists/<int:list_id>")
def detail(list_id):
    lst = query_db("SELECT * FROM lists WHERE id = ?", (list_id,), one=True)
    if not lst:
        flash("List not found", "error")
        return redirect(url_for("lists.index"))

    leads = query_db(
        """SELECT l.* FROM leads l
           JOIN list_leads ll ON l.id = ll.lead_id
           WHERE ll.list_id = ?
           ORDER BY CAST(l.rank AS INTEGER)""",
        (list_id,),
    )

    return render_template("lists/detail.html", lst=lst, leads=leads)


@bp.route("/lists/<int:list_id>/enrich", methods=["POST"])
def enrich(list_id):
    lst = query_db("SELECT * FROM lists WHERE id = ?", (list_id,), one=True)
    if not lst:
        flash("List not found", "error")
        return redirect(url_for("lists.index"))

    db = get_db()
    db.execute("UPDATE lists SET enrichment_status = 'enriching_urls' WHERE id = ?", (list_id,))
    db.commit()

    # Run enrichment in background thread
    app = current_app._get_current_object()

    def run_enrichment():
        from enrichment.pipeline import enrich_list
        with app.app_context():
            enrich_list(list_id)

    thread = threading.Thread(target=run_enrichment, daemon=True)
    thread.start()

    flash("Enrichment started. Progress will update automatically.", "info")
    return redirect(url_for("lists.detail", list_id=list_id))
