import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from tools import db

board_bp = Blueprint("board", __name__)


@board_bp.route("/")
@login_required
def dashboard():
    boards = db.query(
        """SELECT b.*, COUNT(c.id) as card_count
           FROM boards b
           LEFT JOIN cards c ON c.board_id = b.id
           WHERE b.owner_id = ?
              OR b.id IN (SELECT board_id FROM board_members WHERE user_id = ?)
           GROUP BY b.id
           ORDER BY b.updated_at DESC""",
        (current_user.id, current_user.id),
    )
    pending_emails = db.query_one(
        "SELECT COUNT(*) as cnt FROM emails WHERE processed = 0"
    )
    return render_template(
        "dashboard.html",
        boards=boards,
        pending_email_count=pending_emails["cnt"] if pending_emails else 0,
    )


@board_bp.route("/boards", methods=["POST"])
@login_required
def create_board():
    title = request.form.get("title", "").strip()
    sales_team = request.form.get("sales_team", "").strip()
    customer = request.form.get("customer", "").strip()
    brand_site = request.form.get("brand_site", "").strip()
    category = request.form.get("category", "").strip()

    if not title:
        flash("Board title is required.", "error")
        return redirect(url_for("board.dashboard"))

    board_id = str(uuid.uuid4())
    db.execute(
        """INSERT INTO boards (id, title, owner_id, sales_team, customer, brand_site, category)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (board_id, title, current_user.id, sales_team, customer, brand_site, category),
    )
    return redirect(url_for("board.view_board", board_id=board_id))


@board_bp.route("/boards/<board_id>")
@login_required
def view_board(board_id):
    board = db.query_one("SELECT * FROM boards WHERE id = ?", (board_id,))
    if not board:
        flash("Board not found.", "error")
        return redirect(url_for("board.dashboard"))
    # Check access
    if board["owner_id"] != current_user.id:
        member = db.query_one(
            "SELECT * FROM board_members WHERE board_id = ? AND user_id = ?",
            (board_id, current_user.id),
        )
        if not member:
            flash("Access denied.", "error")
            return redirect(url_for("board.dashboard"))
    return render_template("board.html", board=board)


@board_bp.route("/boards/<board_id>/delete", methods=["POST"])
@login_required
def delete_board(board_id):
    board = db.query_one("SELECT * FROM boards WHERE id = ?", (board_id,))
    if not board or board["owner_id"] != current_user.id:
        flash("Cannot delete this board.", "error")
        return redirect(url_for("board.dashboard"))

    # Simple delete - CASCADE should handle related data
    operations = [
        ("PRAGMA foreign_keys = OFF", ()),
        ("DELETE FROM boards WHERE id = ?", (board_id,)),
        ("PRAGMA foreign_keys = ON", ()),
    ]
    db.execute_many(operations)

    flash("Board deleted.", "success")
    return redirect(url_for("board.dashboard"))


@board_bp.route("/boards/<board_id>/settings", methods=["POST"])
@login_required
def update_board(board_id):
    board = db.query_one("SELECT * FROM boards WHERE id = ?", (board_id,))
    if not board:
        flash("Board not found.", "error")
        return redirect(url_for("board.dashboard"))

    title = request.form.get("title", "").strip() or board["title"]
    view_mode = request.form.get("view_mode", board["view_mode"])
    if view_mode not in ("flowchart", "freeform"):
        view_mode = board["view_mode"]
    db.execute(
        "UPDATE boards SET title = ?, view_mode = ?, updated_at = datetime('now') WHERE id = ?",
        (title, view_mode, board_id),
    )
    # If called via JS (no redirect needed), return JSON
    if request.headers.get("Content-Type", "").startswith("application/x-www-form-urlencoded"):
        from flask import jsonify
        return jsonify({"ok": True})
    return redirect(url_for("board.view_board", board_id=board_id))


@board_bp.route("/boards/<board_id>/edit", methods=["POST"])
@login_required
def edit_board(board_id):
    board = db.query_one("SELECT * FROM boards WHERE id = ?", (board_id,))
    if not board or board["owner_id"] != current_user.id:
        flash("Cannot edit this board.", "error")
        return redirect(url_for("board.dashboard"))

    title = request.form.get("title", "").strip()
    sales_team = request.form.get("sales_team", "").strip()
    customer = request.form.get("customer", "").strip()
    brand_site = request.form.get("brand_site", "").strip()
    category = request.form.get("category", "").strip()

    if not title:
        flash("Board title is required.", "error")
        return redirect(url_for("board.dashboard"))

    db.execute(
        """UPDATE boards SET title = ?, sales_team = ?, customer = ?, brand_site = ?, category = ?, updated_at = datetime('now')
           WHERE id = ?""",
        (title, sales_team, customer, brand_site, category, board_id),
    )

    flash("Board updated successfully.", "success")
    return redirect(url_for("board.dashboard"))
