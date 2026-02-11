from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import get_db, query_db

bp = Blueprint("templates", __name__)

PLATFORM_CHOICES = [
    ("all", "All Platforms"),
    ("facebook", "Facebook"),
    ("linkedin", "LinkedIn"),
    ("instagram", "Instagram"),
    ("twitter_x", "Twitter/X"),
    ("youtube", "YouTube"),
    ("tiktok", "TikTok"),
    ("email", "Email"),
]


@bp.route("/templates")
def index():
    templates = query_db("SELECT * FROM message_templates ORDER BY created_at DESC")
    return render_template(
        "templates/index.html", templates=templates, platforms=PLATFORM_CHOICES
    )


@bp.route("/templates/add", methods=["POST"])
def add():
    name = request.form.get("name", "").strip()
    platform = request.form.get("platform", "all")
    content = request.form.get("content", "").strip()

    if not name or not content:
        flash("Name and content are required", "error")
        return redirect(url_for("templates.index"))

    valid_platforms = [p[0] for p in PLATFORM_CHOICES]
    if platform not in valid_platforms:
        flash("Invalid platform", "error")
        return redirect(url_for("templates.index"))

    db = get_db()
    db.execute(
        "INSERT INTO message_templates (name, platform, content) VALUES (?, ?, ?)",
        (name, platform, content),
    )
    db.commit()
    flash(f'Template "{name}" created', "success")
    return redirect(url_for("templates.index"))


@bp.route("/templates/<int:template_id>/delete", methods=["POST"])
def delete(template_id):
    db = get_db()
    db.execute("DELETE FROM message_templates WHERE id = ?", (template_id,))
    db.commit()
    flash("Template deleted", "success")
    return redirect(url_for("templates.index"))
