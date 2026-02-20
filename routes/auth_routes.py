from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from tools.auth import User, check_honeypot

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if check_honeypot(request.form, "website"):
            return redirect(url_for("auth.login"))
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = User.verify_password(email, password)
        if user:
            login_user(user)
            return redirect(url_for("board.dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if check_honeypot(request.form, "company"):
            return redirect(url_for("auth.register"))
        email = request.form.get("email", "").strip()
        display_name = request.form.get("display_name", "").strip()
        password = request.form.get("password", "")
        if not email or not display_name or not password:
            flash("All fields are required.", "error")
            return render_template("register.html")
        if User.get_by_email(email):
            flash("Email already registered.", "error")
            return render_template("register.html")
        user = User.create(email, display_name, password)
        login_user(user)
        return redirect(url_for("board.dashboard"))
    return render_template("register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
