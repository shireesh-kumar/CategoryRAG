from __future__ import annotations

import atexit
import logging

from flask import Flask, jsonify

from categoryrag.config import ensure_data_dirs
from categoryrag.database.db import init_db
from categoryrag.exceptions import NotFoundError, ValidationError
from categoryrag.routes import api_bp
from categoryrag.services.ingest import ingest_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


def create_app() -> Flask:
    ensure_data_dirs()
    init_db()
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    _register_error_handlers(app)
    atexit.register(ingest_worker.shutdown)
    return app


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(NotFoundError)
    def handle_not_found(exc: NotFoundError):
        return jsonify({"error": exc.error, "details": exc.details}), 404

    @app.errorhandler(ValidationError)
    def handle_validation(exc: ValidationError):
        return jsonify({"error": exc.error, "details": exc.details}), 400


def main() -> None:
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)


if __name__ == "__main__":
    main()
