import time
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import get_db, query_db

bp = Blueprint("leads", __name__)

PER_PAGE = 25


@bp.route("/leads")
def index():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()
    platform = request.args.get("platform", "")
    role = request.args.get("role", "")
    city = request.args.get("city", "")
    sort = request.args.get("sort", "rank")
    list_id = request.args.get("list_id", "", type=str)
    show_archived = request.args.get("show_archived", "")

    where_clauses = []
    params = []

    if search:
        where_clauses.append("(leads.name LIKE ? OR leads.company LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    if platform:
        col = platform if platform != "twitter_x" else "twitter_x"
        if platform == "email":
            where_clauses.append("leads.email != '' AND leads.email IS NOT NULL")
        else:
            where_clauses.append(f"leads.{col} != '' AND leads.{col} IS NOT NULL")

    if role:
        where_clauses.append("leads.lo_role = ?")
        params.append(role)

    if city:
        where_clauses.append("leads.city = ?")
        params.append(city)

    if list_id:
        where_clauses.append("leads.id IN (SELECT lead_id FROM list_leads WHERE list_id = ?)")
        params.append(int(list_id))

    # Archive filter
    if show_archived == "only":
        where_clauses.append("leads.id IN (SELECT DISTINCT lead_id FROM outreach_logs WHERE result = 'sent')")
    elif show_archived == "all":
        pass  # no filter
    else:
        # Default: exclude contacted leads
        where_clauses.append("leads.id NOT IN (SELECT DISTINCT lead_id FROM outreach_logs WHERE result = 'sent')")

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    sort_map = {
        "rank": "CAST(leads.rank AS INTEGER)",
        "name": "leads.name",
        "volume": "CAST(REPLACE(REPLACE(leads.volume_export, ',', ''), '$', '') AS INTEGER) DESC",
        "company": "leads.company",
    }
    order_sql = sort_map.get(sort, "CAST(leads.rank AS INTEGER)")

    total = query_db(f"SELECT COUNT(*) as c FROM leads WHERE {where_sql}", params, one=True)["c"]
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * PER_PAGE

    leads = query_db(
        f"SELECT * FROM leads WHERE {where_sql} ORDER BY {order_sql} LIMIT ? OFFSET ?",
        params + [PER_PAGE, offset],
    )

    # Get distinct cities for filter dropdown
    cities = query_db("SELECT DISTINCT city FROM leads WHERE city != '' ORDER BY city")

    # Get lists for filter dropdown
    lists = query_db("SELECT id, name FROM lists ORDER BY name")

    # Count contacted leads (for tab badge)
    archived_count = query_db(
        "SELECT COUNT(DISTINCT lead_id) as c FROM outreach_logs WHERE result = 'sent'",
        one=True,
    )["c"]

    return render_template(
        "leads/index.html",
        leads=leads,
        page=page,
        total_pages=total_pages,
        total=total,
        search=search,
        platform=platform,
        role=role,
        city=city,
        sort=sort,
        cities=cities,
        lists=lists,
        list_id=list_id,
        show_archived=show_archived,
        archived_count=archived_count,
    )


@bp.route("/leads/add", methods=["POST"])
def add_lead():
    name = request.form.get("name", "").strip()
    company = request.form.get("company", "").strip()
    city = request.form.get("city", "").strip()
    email = request.form.get("email", "").strip()
    facebook = request.form.get("facebook", "").strip()
    linkedin = request.form.get("linkedin", "").strip()
    instagram = request.form.get("instagram", "").strip()
    twitter_x = request.form.get("twitter_x", "").strip()
    youtube = request.form.get("youtube", "").strip()
    tiktok = request.form.get("tiktok", "").strip()

    if not name:
        flash("Name is required.", "error")
        return redirect(url_for("leads.index"))

    nmlsid = f"MANUAL-{int(time.time())}"

    db = get_db()
    cur = db.execute(
        """INSERT INTO leads (nmlsid, name, company, city, email,
           facebook, linkedin, instagram, twitter_x, youtube, tiktok)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (nmlsid, name, company, city, email,
         facebook, linkedin, instagram, twitter_x, youtube, tiktok),
    )
    lead_id = cur.lastrowid

    # Link to "All TX Non-QM Brokers" list (id=1) if it exists
    existing_list = db.execute("SELECT id FROM lists WHERE id = 1").fetchone()
    if existing_list:
        db.execute(
            "INSERT OR IGNORE INTO list_leads (list_id, lead_id) VALUES (?, ?)",
            (1, lead_id),
        )

    db.commit()
    flash(f"Lead '{name}' added successfully.", "success")
    return redirect(url_for("leads.index"))
