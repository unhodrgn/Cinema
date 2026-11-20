"""Cinema Reservation System: Flask application package (the REST API).

The backend returns JSON only. It serves no HTML, no templates and no static files: the
frontend is a separate program (``frontend/``) that calls this API over HTTP.
"""

from flask import Flask

from . import api, auth, cors, database, errors, health, security
from .config import DEFAULT_CONFIG_NAME, get_config_class, load_environment
from .json_provider import ApiJSONProvider


def create_app(config_name=None, config_overrides=None):
    """Create and configure a Flask application.

    config_name       "development" (default) or "testing".
    config_overrides  optional mapping applied after the configuration is loaded,
                      e.g. a test fixture supplying DB_NAME.

    Initialization never opens a PostgreSQL connection and does not need a running
    database server. It raises ``RuntimeError`` if any route has no declared policy.
    """
    config_class = get_config_class(config_name or DEFAULT_CONFIG_NAME)

    if config_class.LOADS_DOTENV:
        load_environment()

    # No static folder and no template folder: nothing is served from this process except
    # JSON, and ``render_template`` has no loader to find a template with.
    app = Flask(__name__, static_folder=None, template_folder=None)
    app.json = ApiJSONProvider(app)
    app.config.from_object(config_class())
    if config_overrides:
        app.config.from_mapping(config_overrides)

    # Components are registered here, after the configuration is loaded. None of them
    # opens a database connection.
    database.init_app(app)
    errors.register_error_handlers(app)
    security.init_app(app)
    # Every protected request resolves its user (id from the token -> current database row).
    security.set_user_loader(app, auth.load_user)
    cors.init_app(app)
    app.register_blueprint(health.bp)
    app.register_blueprint(api.bp)

    # The health endpoints keep their Phase 3 behaviour; they are public by design.
    security.classify(app, {"health.health": security.Policy.PUBLIC,
                            "health.health_db": security.Policy.PUBLIC})
    security.check_route_policies(app)

    return app
