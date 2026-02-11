import csv
import io
from flask import Blueprint, render_template, Response
from models import query_db, get_db

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@bp.route("/dashboard")
def index():
    total_leads = query_db("SELECT COUNT(*) as c FROM leads", one=True)["c"]
    leads_with_email = query_db("SELECT COUNT(*) as c FROM leads WHERE email != '' AND email IS NOT NULL", one=True)["c"]
    leads_with_website = query_db("SELECT COUNT(*) as c FROM leads WHERE company_website != '' AND company_website IS NOT NULL", one=True)["c"]

    platform_counts = {}
    for platform in ["facebook", "linkedin", "instagram", "twitter_x", "youtube", "tiktok"]:
        count = query_db(
            f"SELECT COUNT(*) as c FROM leads WHERE {platform} != '' AND {platform} IS NOT NULL",
            one=True,
        )["c"]
        platform_counts[platform] = count

    lists = query_db("SELECT * FROM lists ORDER BY created_at DESC")
    recent_logs = query_db(
        """SELECT ol.*, l.name as lead_name, l.company
           FROM outreach_logs ol
           JOIN leads l ON ol.lead_id = l.id
           ORDER BY ol.timestamp DESC LIMIT 10"""
    )
    total_sessions = query_db("SELECT COUNT(*) as c FROM outreach_sessions", one=True)["c"]
    total_sent = query_db("SELECT COUNT(*) as c FROM outreach_logs WHERE result = 'sent'", one=True)["c"]
    total_skipped = query_db("SELECT COUNT(*) as c FROM outreach_logs WHERE result = 'skipped'", one=True)["c"]

    return render_template(
        "dashboard.html",
        total_leads=total_leads,
        leads_with_email=leads_with_email,
        leads_with_website=leads_with_website,
        platform_counts=platform_counts,
        lists=lists,
        recent_logs=recent_logs,
        total_sessions=total_sessions,
        total_sent=total_sent,
        total_skipped=total_skipped,
    )


@bp.route("/dashboard/export")
def export_csv():
    leads = query_db("SELECT * FROM leads ORDER BY rank")

    output = io.StringIO()
    writer = csv.writer(output)

    if leads:
        writer.writerow(leads[0].keys())
        for lead in leads:
            writer.writerow(list(lead))

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=leads_export.csv"
    return response
