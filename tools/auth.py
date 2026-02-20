import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from tools import db


class User(UserMixin):
    def __init__(self, id, email, display_name, is_active=True):
        self.id = id
        self.email = email
        self.display_name = display_name
        self._is_active = is_active

    @property
    def is_active(self):
        return bool(self._is_active)

    @staticmethod
    def get_by_id(user_id):
        row = db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        if row:
            return User(row["id"], row["email"], row["display_name"], row["is_active"])
        return None

    @staticmethod
    def get_by_email(email):
        row = db.query_one("SELECT * FROM users WHERE email = ?", (email,))
        if row:
            return User(row["id"], row["email"], row["display_name"], row["is_active"])
        return None

    @staticmethod
    def create(email, display_name, password):
        user_id = str(uuid.uuid4())
        pw_hash = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (id, email, display_name, password_hash) VALUES (?, ?, ?, ?)",
            (user_id, email, display_name, pw_hash),
        )
        return User(user_id, email, display_name)

    @staticmethod
    def verify_password(email, password):
        row = db.query_one("SELECT * FROM users WHERE email = ?", (email,))
        if row and check_password_hash(row["password_hash"], password):
            return User(row["id"], row["email"], row["display_name"], row["is_active"])
        return None


def check_honeypot(form, field_name="website"):
    return bool(form.get(field_name, "").strip())
