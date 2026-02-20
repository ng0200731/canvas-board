import uuid
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from tools import db
from tools.file_handler import save_upload, get_file_url, get_thumb_url, is_image

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _check_board_access(board_id):
    board = db.query_one("SELECT * FROM boards WHERE id = ?", (board_id,))
    if not board:
        return None
    if board["owner_id"] == current_user.id:
        return board
    member = db.query_one(
        "SELECT * FROM board_members WHERE board_id = ? AND user_id = ?",
        (board_id, current_user.id),
    )
    return board if member else None


# ── Cards ──────────────────────────────────────────────────

@api_bp.route("/boards/<board_id>/cards", methods=["GET"])
@login_required
def get_cards(board_id):
    board = _check_board_access(board_id)
    if not board:
        return jsonify({"error": "Access denied"}), 403

    cards = db.query(
        "SELECT * FROM cards WHERE board_id = ? ORDER BY sort_order, created_at",
        (board_id,),
    )

    for card in cards:
        card["files"] = db.query(
            "SELECT * FROM card_files WHERE card_id = ?", (card["id"],)
        )
        for f in card["files"]:
            f["url"] = get_file_url(board_id, f["stored_name"])
            f["thumb_url"] = get_thumb_url(board_id, f["stored_name"])
            f["is_image"] = is_image(f["mime_type"])

        tags = db.query(
            """SELECT t.id, t.name FROM tags t
               JOIN card_tags ct ON ct.tag_id = t.id
               WHERE ct.card_id = ?""",
            (card["id"],),
        )
        card["tags"] = tags

        # Add email info if card is from email
        if card.get("email_id"):
            email = db.query_one(
                "SELECT id, from_addr, subject, body_text FROM emails WHERE id = ?",
                (card["email_id"],)
            )
            card["email"] = email

    connections = db.query(
        "SELECT * FROM connections WHERE board_id = ?", (board_id,)
    )

    return jsonify({"cards": cards, "connections": connections, "view_mode": board["view_mode"]})

@api_bp.route("/boards/<board_id>/cards", methods=["POST"])
@login_required
def create_card(board_id):
    board = _check_board_access(board_id)
    if not board:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    card_id = str(uuid.uuid4())
    title = data.get("title", "Untitled")
    pos_x = data.get("pos_x", 100)
    pos_y = data.get("pos_y", 100)

    max_order = db.query_one(
        "SELECT COALESCE(MAX(sort_order), -1) as mx FROM cards WHERE board_id = ?",
        (board_id,),
    )
    sort_order = (max_order["mx"] if max_order else -1) + 1

    db.execute(
        """INSERT INTO cards (id, board_id, title, pos_x, pos_y, sort_order)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (card_id, board_id, title, pos_x, pos_y, sort_order),
    )
    db.execute(
        "UPDATE boards SET updated_at = datetime('now') WHERE id = ?", (board_id,)
    )

    card = db.query_one("SELECT * FROM cards WHERE id = ?", (card_id,))
    card["files"] = []
    card["tags"] = []
    return jsonify(card), 201


@api_bp.route("/cards/<card_id>", methods=["PATCH"])
@login_required
def update_card(card_id):
    card = db.query_one("SELECT * FROM cards WHERE id = ?", (card_id,))
    if not card:
        return jsonify({"error": "Not found"}), 404

    board = _check_board_access(card["board_id"])
    if not board:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    fields = []
    params = []
    for key in ("title", "body", "pos_x", "pos_y", "sort_order"):
        if key in data:
            fields.append(f"{key} = ?")
            params.append(data[key])

    if fields:
        fields.append("updated_at = datetime('now')")
        params.append(card_id)
        db.execute(f"UPDATE cards SET {', '.join(fields)} WHERE id = ?", params)
        db.execute(
            "UPDATE boards SET updated_at = datetime('now') WHERE id = ?",
            (card["board_id"],),
        )

    return jsonify({"ok": True})


@api_bp.route("/cards/<card_id>", methods=["DELETE"])
@login_required
def delete_card(card_id):
    card = db.query_one("SELECT * FROM cards WHERE id = ?", (card_id,))
    if not card:
        return jsonify({"error": "Not found"}), 404
    board = _check_board_access(card["board_id"])
    if not board:
        return jsonify({"error": "Access denied"}), 403

    db.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    return jsonify({"ok": True})


# ── Files ──────────────────────────────────────────────────

@api_bp.route("/cards/<card_id>/files", methods=["POST"])
@login_required
def upload_files(card_id):
    card = db.query_one("SELECT * FROM cards WHERE id = ?", (card_id,))
    if not card:
        return jsonify({"error": "Not found"}), 404
    board = _check_board_access(card["board_id"])
    if not board:
        return jsonify({"error": "Access denied"}), 403

    uploaded = []
    for f in request.files.getlist("files"):
        meta = save_upload(f, card["board_id"])
        if meta:
            db.execute(
                """INSERT INTO card_files (id, card_id, original_name, stored_name, mime_type, file_size)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (meta["id"], card_id, meta["original_name"], meta["stored_name"],
                 meta["mime_type"], meta["file_size"]),
            )
            meta["url"] = get_file_url(card["board_id"], meta["stored_name"])
            meta["thumb_url"] = get_thumb_url(card["board_id"], meta["stored_name"])
            meta["is_image"] = is_image(meta["mime_type"])
            uploaded.append(meta)

    return jsonify({"files": uploaded}), 201


@api_bp.route("/files/<file_id>", methods=["DELETE"])
@login_required
def delete_file(file_id):
    f = db.query_one("SELECT * FROM card_files WHERE id = ?", (file_id,))
    if not f:
        return jsonify({"error": "Not found"}), 404
    db.execute("DELETE FROM card_files WHERE id = ?", (file_id,))
    return jsonify({"ok": True})


# ── Tags ───────────────────────────────────────────────────

@api_bp.route("/cards/<card_id>/tags", methods=["POST"])
@login_required
def add_tag(card_id):
    card = db.query_one("SELECT * FROM cards WHERE id = ?", (card_id,))
    if not card:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json() or {}
    tag_name = data.get("name", "").strip().lower()
    if not tag_name:
        return jsonify({"error": "Tag name required"}), 400

    tag = db.query_one("SELECT * FROM tags WHERE name = ?", (tag_name,))
    if not tag:
        tag_id = str(uuid.uuid4())
        db.execute("INSERT INTO tags (id, name) VALUES (?, ?)", (tag_id, tag_name))
    else:
        tag_id = tag["id"]

    existing = db.query_one(
        "SELECT * FROM card_tags WHERE card_id = ? AND tag_id = ?",
        (card_id, tag_id),
    )
    if not existing:
        db.execute(
            "INSERT INTO card_tags (card_id, tag_id) VALUES (?, ?)",
            (card_id, tag_id),
        )

    return jsonify({"id": tag_id, "name": tag_name}), 201


@api_bp.route("/cards/<card_id>/tags/<tag_id>", methods=["DELETE"])
@login_required
def remove_tag(card_id, tag_id):
    db.execute(
        "DELETE FROM card_tags WHERE card_id = ? AND tag_id = ?",
        (card_id, tag_id),
    )
    return jsonify({"ok": True})


# ── Connections ────────────────────────────────────────────

@api_bp.route("/boards/<board_id>/connections", methods=["POST"])
@login_required
def create_connection(board_id):
    board = _check_board_access(board_id)
    if not board:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    from_id = data.get("from_card_id")
    to_id = data.get("to_card_id")
    if not from_id or not to_id or from_id == to_id:
        return jsonify({"error": "Invalid connection"}), 400

    conn_id = str(uuid.uuid4())
    db.execute(
        """INSERT INTO connections (id, board_id, from_card_id, to_card_id)
           VALUES (?, ?, ?, ?)""",
        (conn_id, board_id, from_id, to_id),
    )
    return jsonify({"id": conn_id, "from_card_id": from_id, "to_card_id": to_id}), 201


@api_bp.route("/connections/<conn_id>", methods=["DELETE"])
@login_required
def delete_connection(conn_id):
    db.execute("DELETE FROM connections WHERE id = ?", (conn_id,))
    return jsonify({"ok": True})


@api_bp.route("/search/tags", methods=["GET"])
@login_required
def search_tags_global():
    q = request.args.get("q", "").strip().lower()
    if not q:
        return jsonify({"boards": []})

    results = db.query(
        """SELECT DISTINCT b.id, b.title
           FROM boards b
           JOIN cards c ON c.board_id = b.id
           JOIN card_tags ct ON ct.card_id = c.id
           JOIN tags t ON t.id = ct.tag_id
           WHERE (b.owner_id = ? OR b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))
             AND LOWER(t.name) LIKE ?
           ORDER BY b.updated_at DESC""",
        (current_user.id, current_user.id, f"%{q}%"),
    )
    return jsonify({"boards": [{"id": r["id"], "title": r["title"]} for r in results]})


# ── Search ─────────────────────────────────────────────────

@api_bp.route("/boards/<board_id>/search", methods=["GET"])
@login_required
def search_cards(board_id):
    board = _check_board_access(board_id)
    if not board:
        return jsonify({"error": "Access denied"}), 403

    q = request.args.get("q", "").strip().lower()
    if not q:
        return jsonify({"card_ids": []})

    results = db.query(
        """SELECT DISTINCT c.id FROM cards c
           LEFT JOIN card_tags ct ON ct.card_id = c.id
           LEFT JOIN tags t ON t.id = ct.tag_id
           WHERE c.board_id = ?
             AND (LOWER(c.title) LIKE ? OR LOWER(t.name) LIKE ?)""",
        (board_id, f"%{q}%", f"%{q}%"),
    )
    return jsonify({"card_ids": [r["id"] for r in results]})


@api_bp.route("/boards/<board_id>/images", methods=["GET"])
@login_required
def get_board_images(board_id):
    board = _check_board_access(board_id)
    if not board:
        return jsonify({"error": "Access denied"}), 403

    images = db.query(
        """SELECT cf.* FROM card_files cf
           JOIN cards c ON c.id = cf.card_id
           WHERE c.board_id = ?
             AND cf.mime_type LIKE 'image/%'
           ORDER BY cf.uploaded_at DESC
           LIMIT 6""",
        (board_id,),
    )

    for img in images:
        img["thumb_url"] = get_thumb_url(board_id, img["stored_name"])

    return jsonify({"images": images})
