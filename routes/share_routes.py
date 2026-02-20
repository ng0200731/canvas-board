import uuid
from flask import Blueprint, request, jsonify, render_template, send_file
from flask_login import login_required, current_user
from tools import db
from tools.file_handler import get_file_url, get_thumb_url, is_image

share_bp = Blueprint("share", __name__)


@share_bp.route("/boards/<board_id>/share", methods=["POST"])
@login_required
def create_share(board_id):
    share_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO shares (id, board_id, created_by) VALUES (?, ?, ?)",
        (share_id, board_id, current_user.id),
    )
    return jsonify({"share_id": share_id, "url": f"/s/{share_id}"})


@share_bp.route("/shares/<share_id>/revoke", methods=["POST"])
@login_required
def revoke_share(share_id):
    db.execute("UPDATE shares SET is_active = 0 WHERE id = ?", (share_id,))
    return jsonify({"ok": True})


@share_bp.route("/s/<share_id>")
def public_board(share_id):
    share = db.query_one(
        "SELECT * FROM shares WHERE id = ? AND is_active = 1", (share_id,)
    )
    if not share:
        return "Link expired or invalid.", 404

    board = db.query_one("SELECT * FROM boards WHERE id = ?", (share["board_id"],))
    if not board:
        return "Board not found.", 404

    cards = db.query(
        "SELECT * FROM cards WHERE board_id = ? ORDER BY sort_order, created_at",
        (board["id"],),
    )
    for card in cards:
        card["files"] = db.query(
            "SELECT * FROM card_files WHERE card_id = ?", (card["id"],)
        )
        for f in card["files"]:
            f["url"] = get_file_url(board["id"], f["stored_name"])
            f["thumb_url"] = get_thumb_url(board["id"], f["stored_name"])
            f["is_image"] = is_image(f["mime_type"])
        card["tags"] = db.query(
            """SELECT t.id, t.name FROM tags t
               JOIN card_tags ct ON ct.tag_id = t.id
               WHERE ct.card_id = ?""",
            (card["id"],),
        )

    connections = db.query(
        "SELECT * FROM connections WHERE board_id = ?", (board["id"],)
    )

    return render_template(
        "board_public.html",
        board=board,
        cards=cards,
        connections=connections,
    )


@share_bp.route("/boards/<board_id>/export", methods=["GET", "POST"])
@login_required
def export_board(board_id):
    fmt = request.args.get("format", "png")
    if request.is_json:
        fmt = request.json.get("format", "png")
    # Find or create a share link for export
    share = db.query_one(
        "SELECT * FROM shares WHERE board_id = ? AND is_active = 1", (board_id,)
    )
    if not share:
        share_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO shares (id, board_id, created_by) VALUES (?, ?, ?)",
            (share_id, board_id, current_user.id),
        )
    else:
        share_id = share["id"]

    try:
        from tools.export_board import export_board as do_export
        path = do_export(share_id, fmt)
        return send_file(path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@share_bp.route("/boards/<board_id>/send", methods=["POST"])
@login_required
def send_board(board_id):
    data = request.get_json() or {}
    to_addr = data.get("to", "").strip()
    if not to_addr:
        return jsonify({"error": "Recipient email required"}), 400

    board = db.query_one("SELECT * FROM boards WHERE id = ?", (board_id,))
    if not board:
        return jsonify({"error": "Board not found"}), 404

    # Export first
    share = db.query_one(
        "SELECT * FROM shares WHERE board_id = ? AND is_active = 1", (board_id,)
    )
    if not share:
        share_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO shares (id, board_id, created_by) VALUES (?, ?, ?)",
            (share_id, board_id, current_user.id),
        )
    else:
        share_id = share["id"]

    try:
        from tools.export_board import export_board as do_export
        from tools.email_sender import send_board_email
        path = do_export(share_id, "pdf")
        send_board_email(
            to_addr,
            f"Board: {board['title']}",
            f"Please find the board '{board['title']}' attached.",
            path,
        )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
