from flask import Blueprint, render_template, request
from models import query_db

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
    )
