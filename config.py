import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
DB_PATH = os.path.join(BASE_DIR, ".tmp", "canva_board.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
EMAIL_ATTACH_DIR = os.path.join(BASE_DIR, ".tmp", "email_attachments")
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

MAIL_USER = os.getenv("MAIL_USER", "")
MAIL_PASS = os.getenv("MAIL_PASS", "")
IMAP_HOST = os.getenv("IMAP_HOST", "")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
