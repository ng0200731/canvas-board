import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from tools import db

email_bp = Blueprint("email", __name__)


@email_bp.route("/emails")
@login_required
def inbox():
    emails = db.query(
        "SELECT * FROM emails ORDER BY created_at DESC"
    )
    return render_template("email_list.html", emails=emails)


@email_bp.route("/emails/<email_id>")
@login_required
def email_detail(email_id):
    em = db.query_one("SELECT * FROM emails WHERE id = ?", (email_id,))
    if not em:
        flash("Email not found.", "error")
        return redirect(url_for("email.inbox"))

    attachments = db.query(
        "SELECT * FROM email_attachments WHERE email_id = ?", (email_id,)
    )
    boards = db.query(
        """SELECT * FROM boards
           WHERE owner_id = ?
              OR id IN (SELECT board_id FROM board_members WHERE user_id = ?)
           ORDER BY updated_at DESC""",
        (current_user.id, current_user.id),
    )
    return render_template(
        "email_detail.html", email=em, attachments=attachments, boards=boards
    )


@email_bp.route("/emails/<email_id>/assign", methods=["POST"])
@login_required
def assign_email(email_id):
    em = db.query_one("SELECT * FROM emails WHERE id = ?", (email_id,))
    if not em:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json() if request.is_json else {}
    board_id = data.get("board_id") or request.form.get("board_id")
    new_board_title = data.get("new_board_title") or request.form.get("new_board_title")

    if new_board_title:
        board_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO boards (id, title, owner_id) VALUES (?, ?, ?)",
            (board_id, new_board_title.strip(), current_user.id),
        )
    elif not board_id:
        flash("Select a board or create a new one.", "error")
        return redirect(url_for("email.email_detail", email_id=email_id))

    # Create a card from the email
    import os, shutil, config
    from tools.file_handler import get_board_upload_dir

    max_order = db.query_one(
        "SELECT COALESCE(MAX(sort_order), -1) as mx FROM cards WHERE board_id = ?",
        (board_id,),
    )
    sort_order = (max_order["mx"] if max_order else -1) + 1

    card_id = str(uuid.uuid4())
    db.execute(
        """INSERT INTO cards (id, board_id, title, body, sort_order)
           VALUES (?, ?, ?, ?, ?)""",
        (card_id, board_id, em["subject"], em["body_text"][:500], sort_order),
    )

    # Move attachments to board uploads
    attachments = db.query(
        "SELECT * FROM email_attachments WHERE email_id = ?", (email_id,)
    )
    upload_dir = get_board_upload_dir(board_id)
    for att in attachments:
        src = os.path.join(config.EMAIL_ATTACH_DIR, att["stored_name"])
        if os.path.exists(src):
            dst = os.path.join(upload_dir, att["stored_name"])
            shutil.copy2(src, dst)
            file_id = str(uuid.uuid4())
            db.execute(
                """INSERT INTO card_files (id, card_id, original_name, stored_name, mime_type, file_size)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (file_id, card_id, att["original_name"], att["stored_name"],
                 att["mime_type"], att["file_size"]),
            )

    # Mark email as processed
    db.execute(
        "UPDATE emails SET processed = 1, board_id = ? WHERE id = ?",
        (board_id, email_id),
    )

    flash("Email assigned to board.", "success")
    return redirect(url_for("board.view_board", board_id=board_id))


@email_bp.route("/emails/<email_id>/ignore", methods=["POST"])
@login_required
def ignore_email(email_id):
    db.execute("UPDATE emails SET processed = 2 WHERE id = ?", (email_id,))
    flash("Email ignored.", "success")
    return redirect(url_for("email.inbox"))


@email_bp.route("/emails/poll", methods=["POST"])
@login_required
def poll_now():
    try:
        from tools.email_poller import poll
        count = poll()
        return jsonify({"ok": True, "fetched": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
