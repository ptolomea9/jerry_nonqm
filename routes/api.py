import json
from flask import Blueprint, request, jsonify
from models import get_db, query_db

bp = Blueprint("api", __name__)


@bp.route("/api/outreach/log", methods=["POST"])
def log_action():
    data = request.get_json()
    session_id = data.get("session_id")
    lead_id = data.get("lead_id")
    result = data.get("result")  # 'sent' or 'skipped'

    if not all([session_id, lead_id, result]):
        return jsonify({"error": "Missing fields"}), 400

    if result not in ("sent", "skipped"):
        return jsonify({"error": "Invalid result"}), 400

    sess = query_db("SELECT * FROM outreach_sessions WHERE id = ?", (session_id,), one=True)
    if not sess:
        return jsonify({"error": "Session not found"}), 404

    db = get_db()

    # Log the action
    db.execute(
        "INSERT INTO outreach_logs (session_id, lead_id, platform, flyer_id, result) VALUES (?, ?, ?, ?, ?)",
        (session_id, lead_id, sess["platform"], sess["flyer_id"], result),
    )

    # Advance session index
    lead_queue = json.loads(sess["lead_queue"])
    new_index = sess["current_index"] + 1

    if new_index >= len(lead_queue):
        db.execute(
            "UPDATE outreach_sessions SET current_index = ?, status = 'complete' WHERE id = ?",
            (new_index, session_id),
        )
    else:
        db.execute(
            "UPDATE outreach_sessions SET current_index = ? WHERE id = ?",
            (new_index, session_id),
        )

    db.commit()

    # Return next lead data or done signal
    if new_index >= len(lead_queue):
        return jsonify({"done": True, "session_id": session_id})

    next_lead_id = lead_queue[new_index]
    lead = query_db("SELECT * FROM leads WHERE id = ?", (next_lead_id,), one=True)

    platform = sess["platform"]
    platform_col_map = {
        "facebook": "facebook", "linkedin": "linkedin",
        "instagram": "instagram", "twitter_x": "twitter_x",
        "youtube": "youtube", "tiktok": "tiktok", "email": "email",
    }
    col = platform_col_map.get(platform, platform)
    profile_url = lead[col] if lead and col in lead.keys() else ""

    return jsonify({
        "done": False,
        "lead": {
            "id": lead["id"],
            "name": lead["name"],
            "company": lead["company"],
            "city": lead["city"],
            "volume": lead["volume"],
            "rank": lead["rank"],
            "profile_url": profile_url,
        },
        "current": new_index + 1,
        "total": len(lead_queue),
    })


@bp.route("/api/lists/<int:list_id>/status")
def list_status(list_id):
    lst = query_db("SELECT * FROM lists WHERE id = ?", (list_id,), one=True)
    if not lst:
        return jsonify({"error": "Not found"}), 404

    total = lst["row_count"]
    enriched = 0
    if lst["enrichment_status"] not in ("none", "pending"):
        leads = query_db(
            """SELECT COUNT(*) as c FROM leads l
               JOIN list_leads ll ON l.id = ll.lead_id
               WHERE ll.list_id = ?
               AND (l.company_website != '' AND l.company_website IS NOT NULL)""",
            (list_id,),
            one=True,
        )
        enriched = leads["c"] if leads else 0

    return jsonify({
        "status": lst["enrichment_status"],
        "total": total,
        "enriched": enriched,
        "progress_pct": int(enriched / total * 100) if total > 0 else 0,
    })
