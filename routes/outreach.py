import json
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import get_db, query_db

bp = Blueprint("outreach", __name__)

PLATFORM_COLUMN_MAP = {
    "facebook": "facebook",
    "linkedin": "linkedin",
    "instagram": "instagram",
    "twitter_x": "twitter_x",
    "youtube": "youtube",
    "tiktok": "tiktok",
    "email": "email",
}


@bp.route("/outreach/setup")
def setup():
    lists = query_db("SELECT * FROM lists ORDER BY created_at DESC")
    flyers = query_db("SELECT * FROM flyers ORDER BY created_at DESC")
    return render_template("outreach/setup.html", lists=lists, flyers=flyers)


@bp.route("/outreach/start", methods=["POST"])
def start():
    list_id = request.form.get("list_id", type=int)
    flyer_id = request.form.get("flyer_id", type=int)
    platform = request.form.get("platform", "")

    if not list_id or not platform:
        flash("Please select a list and platform", "error")
        return redirect(url_for("outreach.setup"))

    col = PLATFORM_COLUMN_MAP.get(platform)
    if not col:
        flash("Invalid platform", "error")
        return redirect(url_for("outreach.setup"))

    # Get leads in this list that have the selected platform AND haven't been contacted yet
    leads = query_db(
        f"""SELECT l.id FROM leads l
            JOIN list_leads ll ON l.id = ll.lead_id
            WHERE ll.list_id = ?
            AND l.{col} != '' AND l.{col} IS NOT NULL
            AND l.id NOT IN (
                SELECT lead_id FROM outreach_logs
                WHERE platform = ? AND result = 'sent'
            )
            ORDER BY CAST(l.rank AS INTEGER)""",
        (list_id, platform),
    )

    if not leads:
        flash("No eligible leads found for this list/platform combination", "warning")
        return redirect(url_for("outreach.setup"))

    lead_queue = [row["id"] for row in leads]

    db = get_db()
    cur = db.execute(
        """INSERT INTO outreach_sessions (list_id, flyer_id, platform, lead_queue, current_index, status)
           VALUES (?, ?, ?, ?, 0, 'active')""",
        (list_id, flyer_id, platform, json.dumps(lead_queue)),
    )
    session_id = cur.lastrowid
    db.commit()

    return redirect(url_for("outreach.session", session_id=session_id))


@bp.route("/outreach/session/<int:session_id>")
def session(session_id):
    sess = query_db("SELECT * FROM outreach_sessions WHERE id = ?", (session_id,), one=True)
    if not sess:
        flash("Session not found", "error")
        return redirect(url_for("outreach.setup"))

    lead_queue = json.loads(sess["lead_queue"])
    current_index = sess["current_index"]

    if current_index >= len(lead_queue):
        return redirect(url_for("outreach.summary", session_id=session_id))

    lead_id = lead_queue[current_index]
    lead = query_db("SELECT * FROM leads WHERE id = ?", (lead_id,), one=True)

    flyer = None
    if sess["flyer_id"]:
        flyer = query_db("SELECT * FROM flyers WHERE id = ?", (sess["flyer_id"],), one=True)

    platform = sess["platform"]
    col = PLATFORM_COLUMN_MAP.get(platform, platform)
    profile_url = lead[col] if lead and col in lead.keys() else ""

    return render_template(
        "outreach/session.html",
        sess=sess,
        lead=lead,
        flyer=flyer,
        profile_url=profile_url,
        current=current_index + 1,
        total=len(lead_queue),
        platform=platform,
    )


@bp.route("/outreach/session/<int:session_id>/summary")
def summary(session_id):
    sess = query_db("SELECT * FROM outreach_sessions WHERE id = ?", (session_id,), one=True)
    if not sess:
        flash("Session not found", "error")
        return redirect(url_for("outreach.setup"))

    logs = query_db(
        """SELECT ol.*, l.name as lead_name, l.company
           FROM outreach_logs ol
           JOIN leads l ON ol.lead_id = l.id
           WHERE ol.session_id = ?
           ORDER BY ol.timestamp""",
        (session_id,),
    )

    sent = sum(1 for log in logs if log["result"] == "sent")
    skipped = sum(1 for log in logs if log["result"] == "skipped")

    return render_template(
        "outreach/summary.html",
        sess=sess,
        logs=logs,
        sent=sent,
        skipped=skipped,
        total=len(logs),
    )
