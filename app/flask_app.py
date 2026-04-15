from flask import Flask

from app.db import db
from app.health.routes import health_bp
from app.logging_setup import init_logging
from app.middleware.request_logger import init_request_logger
from app.starkbank_setup import init_starkbank
from app.webhooks.routes import webhook_bp


def create_app():
    app = Flask(__name__)

    init_logging()
    init_starkbank()

    db.connect(reuse_if_open=True)

    init_request_logger(app)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(health_bp)

    @app.teardown_appcontext
    def close_db(exc):
        if not db.is_closed():
            db.close()

    return app
