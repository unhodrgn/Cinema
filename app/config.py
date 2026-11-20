"""Application configuration.

Settings come from environment variables (optionally loaded from a ``.env`` file).
Nothing secret or environment-specific is hardcoded here; see ``.env.example`` for
the full list of variables.

Configuration classes read the environment when they are *instantiated*, not when
this module is imported, so importing it has no side effects.
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOTENV_PATH = PROJECT_ROOT / ".env"

DEFAULT_TIMEZONE = "Asia/Seoul"
MIN_SECRET_KEY_LENGTH = 16

# Fixed key for the testing configuration only. It is not a secret and is never
# read from the environment, so tests cannot pick up a real key.
TESTING_SECRET_KEY = "testing-only-secret-key-not-for-production"

# Format check only: "UTC", "GMT" or "Area/Location[/Sub]". The tz database is not
# guaranteed to exist on Windows, so PostgreSQL validates the name when connecting.
_TIMEZONE_PATTERN = re.compile(r"^(?:UTC|GMT|[A-Za-z_]+(?:/[A-Za-z0-9_+\-]+)+)$")

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


class ConfigError(ValueError):
    """The configuration is missing or invalid."""


def load_environment(path=None):
    """Load variables from a ``.env`` file into ``os.environ``.

    Variables that are already set in the real environment are never overridden.
    Returns True if a file was found and read.
    """
    return load_dotenv(path or DOTENV_PATH, override=False)


class _EnvReader:
    """Reads typed values from a mapping and collects every problem found."""

    def __init__(self, environ):
        self._environ = environ
        self.errors = []

    def text(self, name, default=None, required=False):
        value = (self._environ.get(name) or "").strip()
        if value:
            return value
        if required:
            self.errors.append(f"{name} is required")
        return default

    def integer(self, name, default, minimum, maximum):
        value = self.text(name)
        if value is None:
            return default
        try:
            number = int(value)
        except ValueError:
            self.errors.append(f"{name} must be an integer (got {value!r})")
            return default
        if not minimum <= number <= maximum:
            self.errors.append(f"{name} must be between {minimum} and {maximum} (got {number})")
            return default
        return number

    def boolean(self, name, default):
        value = self.text(name)
        if value is None:
            return default
        lowered = value.lower()
        if lowered in _TRUE_VALUES:
            return True
        if lowered in _FALSE_VALUES:
            return False
        self.errors.append(f"{name} must be one of 1/0, true/false, yes/no, on/off (got {value!r})")
        return default

    def timezone(self, name, default):
        value = self.text(name)
        if value is None:
            return default
        if not _TIMEZONE_PATTERN.match(value):
            self.errors.append(f"{name} must be an IANA name such as 'Asia/Seoul' (got {value!r})")
            return default
        return value


class Config:
    """Strict base configuration: required values must be present and valid."""

    TESTING = False
    DEBUG = False
    # True when create_app() should load the project's .env file for this config.
    LOADS_DOTENV = True

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    def __init__(self, environ=None):
        reader = _EnvReader(os.environ if environ is None else environ)

        self.SECRET_KEY = self._read_secret_key(reader)
        self.DB_HOST = reader.text("DB_HOST", default="localhost")
        self.DB_PORT = reader.integer("DB_PORT", default=5432, minimum=1, maximum=65535)
        self.DB_NAME = self._read_db_name(reader)
        self.DB_USER = self._read_db_user(reader)
        self.DB_PASSWORD = reader.text("DB_PASSWORD")  # optional: libpq falls back to .pgpass
        self.DB_CONNECT_TIMEOUT = reader.integer(
            "DB_CONNECT_TIMEOUT", default=5, minimum=1, maximum=60
        )
        self.APP_TIMEZONE = reader.timezone("APP_TIMEZONE", default=DEFAULT_TIMEZONE)
        self.DEBUG = self._read_debug(reader)

        if reader.errors:
            problems = "\n".join(f"  - {message}" for message in reader.errors)
            raise ConfigError(
                f"Invalid configuration ({type(self).__name__}):\n{problems}\n"
                "Copy .env.example to .env and fill in the values."
            )

    # Hooks overridden by subclasses ------------------------------------------------

    def _read_secret_key(self, reader):
        value = reader.text("SECRET_KEY", required=True)
        if value is not None and len(value) < MIN_SECRET_KEY_LENGTH:
            # The value itself is never included in the message.
            reader.errors.append(
                f"SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH} characters; generate one "
                'with: python -c "import secrets; print(secrets.token_hex(32))"'
            )
            return None
        return value

    def _read_db_name(self, reader):
        return reader.text("DB_NAME", required=True)

    def _read_db_user(self, reader):
        return reader.text("DB_USER", required=True)

    def _read_debug(self, reader):
        return False

    def __repr__(self):
        # Secrets (SECRET_KEY, DB_PASSWORD) are deliberately left out.
        return (
            f"<{type(self).__name__} DB_HOST={self.DB_HOST!r} DB_PORT={self.DB_PORT!r} "
            f"DB_NAME={self.DB_NAME!r} DB_USER={self.DB_USER!r} "
            f"APP_TIMEZONE={self.APP_TIMEZONE!r} DEBUG={self.DEBUG!r}>"
        )


class DevelopmentConfig(Config):
    """Local development: debug mode is opt-in through FLASK_DEBUG (default off)."""

    def _read_debug(self, reader):
        return reader.boolean("FLASK_DEBUG", default=False)


class TestingConfig(Config):
    """Automated tests.

    Needs no environment at all. The secret key is a fixed non-secret constant and
    DB_NAME is deliberately never read from the environment: it is None until a test
    fixture supplies the name of a disposable ``cinema_test_*`` database, so a test
    can never reach the normal development database by accident.
    """

    TESTING = True
    LOADS_DOTENV = False

    def _read_secret_key(self, reader):
        return TESTING_SECRET_KEY

    def _read_db_name(self, reader):
        return None

    def _read_db_user(self, reader):
        return reader.text("DB_USER")


CONFIG_CLASSES = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
}
DEFAULT_CONFIG_NAME = "development"


def get_config_class(name):
    try:
        return CONFIG_CLASSES[name]
    except KeyError:
        known = ", ".join(sorted(CONFIG_CLASSES))
        raise ConfigError(f"Unknown configuration {name!r}; expected one of: {known}") from None
