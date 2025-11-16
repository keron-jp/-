from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import os

# Local import
from models import db, User, PasswordChangeLog

APP_DB = os.environ.get("APP_DB", "sqlite:///app.db")

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = APP_DB
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # Use a secure random secret key in production (env var)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    db.init_app(app)
    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    def role_required(role_name):
        """Decorator that requires the current_user to have specific role."""
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                if not current_user.is_authenticated:
                    return jsonify({"error": "authentication required"}), 401
                if current_user.role != role_name:
                    return jsonify({"error": "insufficient permissions"}), 403
                return f(*args, **kwargs)
            return wrapped
        return decorator

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    # Register a new user (open sign-up). In many systems sign-up is restricted.
    @app.route("/register", methods=["POST"])
    def register():
        data = request.get_json() or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or not password:
            return jsonify({"error": "username and password required"}), 400
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "username already exists"}), 409

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return jsonify({"message": "user created", "user_id": user.id}), 201

    @app.route("/login", methods=["POST"])
    def login():
        data = request.get_json() or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or not password:
            return jsonify({"error": "username and password required"}), 400
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            # Generic message to avoid user enumeration
            return jsonify({"error": "invalid credentials"}), 401
        login_user(user)
        return jsonify({"message": "logged in", "user_id": user.id}), 200

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        logout_user()
        return jsonify({"message": "logged out"}), 200

    # Change own password (requires current password)
    @app.route("/change_password", methods=["POST"])
    @login_required
    def change_own_password():
        data = request.get_json() or {}
        current_pw = data.get("current_password") or ""
        new_pw = data.get("new_password") or ""
        if not current_pw or not new_pw:
            return jsonify({"error": "current_password and new_password required"}), 400
        if not current_user.check_password(current_pw):
            return jsonify({"error": "current password incorrect"}), 403
        current_user.set_password(new_pw)
        db.session.add(current_user)
        # Log the change
        log = PasswordChangeLog(actor_id=current_user.id, target_id=current_user.id, reason="self-change",
                                ip=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        return jsonify({"message": "password changed"}), 200

    # Password managers can change other users' passwords without knowing current password.
    @app.route("/admin/change_password/<int:user_id>", methods=["POST"])
    @login_required
    def admin_change_password(user_id):
        # Only allow users with role 'password_manager' to call this endpoint
        if current_user.role != "password_manager":
            return jsonify({"error": "insufficient permissions"}), 403
        data = request.get_json() or {}
        new_pw = data.get("new_password") or ""
        reason = data.get("reason") or "admin-reset"
        if not new_pw:
            return jsonify({"error": "new_password required"}), 400
        target = User.query.get(user_id)
        if not target:
            return jsonify({"error": "user not found"}), 404
        target.set_password(new_pw)
        db.session.add(target)
        # Log the change with actor and target
        log = PasswordChangeLog(actor_id=current_user.id, target_id=target.id, reason=reason,
                                ip=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        return jsonify({"message": "target password changed", "target_user_id": target.id}), 200

    # Endpoint to grant manager role to another user (only manager can grant)
    @app.route("/admin/set_manager/<int:user_id>", methods=["POST"])
    @login_required
    def set_manager(user_id):
        if current_user.role != "password_manager":
            return jsonify({"error": "insufficient permissions"}), 403
        target = User.query.get(user_id)
        if not target:
            return jsonify({"error": "user not found"}), 404
        target.role = "password_manager"
        db.session.commit()
        return jsonify({"message": "role updated", "user_id": target.id, "new_role": target.role}), 200

    # List password change logs (managers only)
    @app.route("/admin/logs", methods=["GET"])
    @login_required
    def view_logs():
        if current_user.role != "password_manager":
            return jsonify({"error": "insufficient permissions"}), 403
        logs = PasswordChangeLog.query.order_by(PasswordChangeLog.timestamp.desc()).limit(200).all()
        data = []
        for l in logs:
            data.append({
                "id": l.id,
                "actor_id": l.actor_id,
                "target_id": l.target_id,
                "reason": l.reason,
                "ip": l.ip,
                "timestamp": l.timestamp.isoformat(),
            })
        return jsonify({"logs": data}), 200

    return app

if __name__ == "__main__":
    app = create_app()
    # Create DB/tables if necessary (development convenience)
    with app.app_context():
        db.create_all()
    # For production, use a WSGI server (gunicorn / uvicorn) and HTTPS
    app.run(host="0.0.0.0", port=5000, debug=True)