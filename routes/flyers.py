import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
import config
from models import get_db, query_db

bp = Blueprint("flyers", __name__)


@bp.route("/flyers")
def index():
    flyers = query_db("SELECT * FROM flyers ORDER BY created_at DESC")
    return render_template("flyers/index.html", flyers=flyers)


@bp.route("/flyers/upload", methods=["POST"])
def upload():
    if "flyer_file" not in request.files:
        flash("No file selected", "error")
        return redirect(url_for("flyers.index"))

    file = request.files["flyer_file"]
    if file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("flyers.index"))

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in config.ALLOWED_IMAGE_EXTENSIONS:
        flash("Only image files (PNG, JPG, GIF, PDF) are allowed", "error")
        return redirect(url_for("flyers.index"))

    flyer_name = request.form.get("flyer_name", "").strip() or file.filename
    tags = request.form.get("tags", "").strip()

    os.makedirs(config.UPLOAD_FOLDER_FLYERS, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(config.UPLOAD_FOLDER_FLYERS, stored_name)
    file.save(filepath)

    db = get_db()
    db.execute(
        "INSERT INTO flyers (name, stored_path, file_type, tags) VALUES (?, ?, ?, ?)",
        (flyer_name, stored_name, ext, tags),
    )
    db.commit()

    flash(f"Flyer '{flyer_name}' uploaded", "success")
    return redirect(url_for("flyers.index"))


@bp.route("/flyers/<int:flyer_id>/preview")
def preview(flyer_id):
    flyer = query_db("SELECT * FROM flyers WHERE id = ?", (flyer_id,), one=True)
    if not flyer:
        return "Not found", 404
    return send_from_directory(config.UPLOAD_FOLDER_FLYERS, flyer["stored_path"])


@bp.route("/flyers/<int:flyer_id>/delete", methods=["POST"])
def delete(flyer_id):
    flyer = query_db("SELECT * FROM flyers WHERE id = ?", (flyer_id,), one=True)
    if flyer:
        filepath = os.path.join(config.UPLOAD_FOLDER_FLYERS, flyer["stored_path"])
        if os.path.exists(filepath):
            os.remove(filepath)
        db = get_db()
        db.execute("DELETE FROM flyers WHERE id = ?", (flyer_id,))
        db.commit()
        flash("Flyer deleted", "success")
    return redirect(url_for("flyers.index"))
