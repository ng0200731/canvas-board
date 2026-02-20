import os
import uuid
from email import policy
from email.header import decode_header
import imapclient
import config
from tools import db


def poll():
    """Connect to IMAP, fetch unseen emails, store in DB. Returns count fetched."""
    server = imapclient.IMAPClient(config.IMAP_HOST, port=config.IMAP_PORT, ssl=True)
    server.login(config.MAIL_USER, config.MAIL_PASS)
    server.select_folder("INBOX")

    uids = server.search(["UNSEEN"])
    count = 0

    for uid in uids:
        uid_str = str(uid)
        # Dedup
        existing = db.query_one("SELECT id FROM emails WHERE imap_uid = ?", (uid_str,))
        if existing:
            continue

        raw = server.fetch([uid], ["RFC822"])
        if uid not in raw:
            continue

        import email as email_lib
        msg = email_lib.message_from_bytes(raw[uid][b"RFC822"], policy=policy.default)

        subject = msg.get("Subject", "(no subject)")
        from_addr = msg.get("From", "")
        date_str = msg.get("Date", "")

        body_text = ""
        body_html = ""
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                cd = part.get("Content-Disposition", "")
                if "attachment" in cd or part.get_filename():
                    att_data = part.get_payload(decode=True)
                    if att_data:
                        fname = part.get_filename() or "attachment"
                        attachments.append({
                            "filename": fname,
                            "data": att_data,
                            "mime_type": ct,
                        })
                elif ct == "text/plain" and not body_text:
                    body_text = part.get_payload(decode=True).decode("utf-8", errors="replace")
                elif ct == "text/html" and not body_html:
                    body_html = part.get_payload(decode=True).decode("utf-8", errors="replace")
        else:
            ct = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                text = payload.decode("utf-8", errors="replace")
                if ct == "text/html":
                    body_html = text
                else:
                    body_text = text

        email_id = str(uuid.uuid4())
        db.execute(
            """INSERT INTO emails (id, imap_uid, from_addr, subject, body_text, body_html, received_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (email_id, uid_str, from_addr, subject, body_text, body_html, date_str),
        )

        # Save attachments
        os.makedirs(config.EMAIL_ATTACH_DIR, exist_ok=True)
        for att in attachments:
            att_id = str(uuid.uuid4())
            ext = os.path.splitext(att["filename"])[1] or ""
            stored_name = f"{att_id}{ext}"
            save_path = os.path.join(config.EMAIL_ATTACH_DIR, stored_name)
            with open(save_path, "wb") as f:
                f.write(att["data"])
            db.execute(
                """INSERT INTO email_attachments (id, email_id, original_name, stored_name, mime_type, file_size)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (att_id, email_id, att["filename"], stored_name, att["mime_type"], len(att["data"])),
            )

        count += 1

    server.logout()
    return count
