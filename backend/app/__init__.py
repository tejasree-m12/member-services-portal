"""Member Services Portal - backend application package.

``create_app`` is an "application factory": a function that builds and
returns a configured Flask app. Tests call it with a test configuration to
get a fresh, isolated app; gunicorn calls it once for production.
"""
import logging

from flask import Flask, jsonify
from sqlalchemy import text

from .config import Config
from .errors import register_error_handlers
from .extensions import cors, db, jwt


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    if not app.debug and not app.testing:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

    # Each module is a Blueprint: a group of related routes in its own folder.
    from .admin.routes import bp as admin_bp
    from .auth.routes import bp as auth_bp
    from .claims.routes import bp as claims_bp
    from .dashboard.routes import bp as dashboard_bp
    from .members.routes import bp as members_bp
    from .providers.routes import bp as providers_bp

    for blueprint in (auth_bp, members_bp, providers_bp, claims_bp, dashboard_bp, admin_bp):
        app.register_blueprint(blueprint)

    register_error_handlers(app)

    from .cli import register_cli

    register_cli(app)

    @app.get("/api/v1/health")
    def health():
        """Used by the load balancer / deploy script to check the app is up."""
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            app.logger.exception("Health check: database unreachable")
            return jsonify({"status": "degraded", "database": "unreachable"}), 503
        return jsonify({"status": "ok", "database": "ok"})

    return app
