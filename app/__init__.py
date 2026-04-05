import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."


def create_app(env=None):
    app = Flask(__name__, instance_relative_config=True)

    from app.config import config
    env = env or os.environ.get("FLASK_ENV", "default")
    app.config.from_object(config.get(env, config["default"]))

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.public import public_bp
    from app.routes.teacher import teacher_bp
    from app.routes.superuser import superuser_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(teacher_bp, url_prefix="/teacher")
    app.register_blueprint(superuser_bp, url_prefix="/admin")

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("errors/500.html"), 500

    with app.app_context():
        db.create_all()
        _seed_superuser()
        _seed_default_settings()
        _start_scheduler(app)

    return app


def _seed_superuser():
    from app.models import User
    import bcrypt

    superuser = User.query.filter_by(role="superuser").first()
    if not superuser:
        email = os.environ.get("SUPERUSER_EMAIL", "admin@example.com")
        password = os.environ.get("SUPERUSER_PASSWORD", "changeme123").encode()
        hashed = bcrypt.hashpw(password, bcrypt.gensalt()).decode()
        superuser = User(
            name="Admin",
            email=email,
            password_hash=hashed,
            role="superuser",
        )
        db.session.add(superuser)
        db.session.commit()
        print("Superuser created. Please change your password after first login.")


def _seed_default_settings():
    from app.models import GlobalSettings

    if not GlobalSettings.query.first():
        settings = GlobalSettings(
            confirmation_required_before_days=7,
            reminder_days_before=1,
        )
        db.session.add(settings)
        db.session.commit()


def _start_scheduler(app):
    from app.services.jobs import start_scheduler
    start_scheduler(app)
