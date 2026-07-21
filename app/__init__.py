from flask import Flask, render_template

from .config import Config
from .extensions import db, limiter


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    (app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)
    (app.config["CARD_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        (Config.UPLOAD_DIR.parent.parent / "instance").mkdir(exist_ok=True)

    db.init_app(app)
    limiter.init_app(app)

    from .routes.public import bp as public_bp
    from .routes.admin import bp as admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.errorhandler(404)
    def not_found(e):
        # Plan §4: "This page is missing. Accountability, bhi."
        return render_template("404.html"), 404

    @app.errorhandler(429)
    def rate_limited(e):
        return render_template("429.html"), 429

    @app.context_processor
    def inject_globals():
        from .services.util import letters_count, slots_left

        return {
            "letters_count": letters_count,
            "slots_left": slots_left,
            "TIERS": app.config["TIERS"],
            "cfg": app.config,
        }

    with app.app_context():
        db.create_all()
        from .letter_templates import seed_templates

        seed_templates()

    return app
