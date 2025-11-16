from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    # role: "user" (default) or "password_manager"
    role = db.Column(db.String(50), default="user", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        # Use a strong hashing algorithm. Werkzeug's default PBKDF2 is acceptable;
        # consider using bcrypt or Argon2 in production (e.g., passlib).
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_manager(self) -> bool:
        return self.role == "password_manager"

class PasswordChangeLog(db.Model):
    __tablename__ = "password_change_logs"
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)  # who changed the password
    target_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)  # whose password was changed
    reason = db.Column(db.String(255), nullable=True)
    ip = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)