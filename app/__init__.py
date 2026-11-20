"""Cinema Reservation System: Flask application package."""

from flask import Flask

from . import database, errors, health
from .config import DEFAULT_CONFIG_NAME, get_config_class, load_environment


def create_app(config_name=None, config_overrides=None):
    """Create and configure a Flask application.

    config_name       "development" (default) or "testing".
    config_overrides  optional mapping applied after the configuration is loaded,
                      e.g. a test fixture supplying DB_NAME.

    Initialization never opens a PostgreSQL connection and does not need a running
    database server.
    """
    config_class = get_config_class(config_name or DEFAULT_CONFIG_NAME)

    if config_class.LOADS_DOTENV:
        load_environment()

    app = Flask(__name__)
    app.config.from_object(config_class())
    if config_overrides:
        app.config.from_mapping(config_overrides)

    # Components are registered here, after the configuration is loaded. None of them
    # opens a database connection.
    database.init_app(app)
    errors.register_error_handlers(app)
    app.register_blueprint(health.bp)

    return app
