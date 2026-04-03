import bcrypt
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db, login_manager
from app.models import User

auth_bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").encode()
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.checkpw(password, user.password_hash.encode()):
            login_user(user)
            return _redirect_by_role(user)

        flash("Invalid email or password.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("public.index"))


def _redirect_by_role(user):
    if user.is_superuser():
        return redirect(url_for("superuser.dashboard"))
    return redirect(url_for("teacher.dashboard"))
