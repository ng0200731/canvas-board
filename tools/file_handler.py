import os
import uuid
from PIL import Image
import config

ALLOWED_EXTENSIONS = {
    "image": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"},
    "document": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"},
}

ALL_ALLOWED = ALLOWED_EXTENSIONS["image"] | ALLOWED_EXTENSIONS["document"]

THUMB_SIZE = (300, 300)


def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALL_ALLOWED


def get_board_upload_dir(board_id):
    path = os.path.join(config.UPLOAD_DIR, board_id)
    os.makedirs(path, exist_ok=True)
    return path


def get_thumb_dir(board_id):
    path = os.path.join(config.UPLOAD_DIR, board_id, "thumbs")
    os.makedirs(path, exist_ok=True)
    return path


def save_upload(file_storage, board_id):
    """Save an uploaded file. Returns dict with file metadata or None."""
    original_name = file_storage.filename
    if not original_name or not allowed_file(original_name):
        return None

    ext = os.path.splitext(original_name)[1].lower()
    file_id = str(uuid.uuid4())
    stored_name = f"{file_id}{ext}"

    upload_dir = get_board_upload_dir(board_id)
    save_path = os.path.join(upload_dir, stored_name)
    file_storage.save(save_path)

    file_size = os.path.getsize(save_path)
    mime_type = file_storage.content_type or "application/octet-stream"

    # Generate thumbnail for images
    if ext in ALLOWED_EXTENSIONS["image"] and ext != ".svg":
        try:
            generate_thumbnail(save_path, board_id, stored_name)
        except Exception:
            pass

    return {
        "id": file_id,
        "original_name": original_name,
        "stored_name": stored_name,
        "mime_type": mime_type,
        "file_size": file_size,
    }


def generate_thumbnail(image_path, board_id, stored_name):
    thumb_dir = get_thumb_dir(board_id)
    thumb_path = os.path.join(thumb_dir, stored_name)
    with Image.open(image_path) as img:
        img.thumbnail(THUMB_SIZE)
        img.save(thumb_path)


def get_file_url(board_id, stored_name):
    return f"/static/uploads/{board_id}/{stored_name}"


def get_thumb_url(board_id, stored_name):
    thumb_path = os.path.join(config.UPLOAD_DIR, board_id, "thumbs", stored_name)
    if os.path.exists(thumb_path):
        return f"/static/uploads/{board_id}/thumbs/{stored_name}"
    return get_file_url(board_id, stored_name)


def is_image(mime_type):
    return mime_type and mime_type.startswith("image/")
