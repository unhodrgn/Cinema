"""T1: docs/api/api_contract.md must agree with the code it documents."""

import re
from pathlib import Path

from app import create_app
from app.errors import (
    DATABASE_UNAVAILABLE,
    HTTP_ERRORS,
    INTERNAL_ERROR,
    INVALID_CREDENTIALS,
    INVALID_JSON,
    SCREENING_STARTED,
    SQLSTATE_ERRORS,
    VALIDATION_ERROR,
)

CONTRACT = Path(__file__).resolve().parents[1] / "docs" / "api" / "api_contract.md"
TEXT = CONTRACT.read_text(encoding="utf-8")


def section(number):
    return TEXT.split(f"\n## {number}.", 1)[1].split("\n## ", 1)[0]


def normalized(path):
    """``/api/movies/<int:movie_id>`` and ``/api/movies/{id}`` both become ``/api/movies/{id}``."""
    return re.sub(r"<[^>]+>|\{[^}]+\}", "{id}", path)


def documented_errors():
    rows = re.findall(r"^\| (\d{3}) \| `([a-z_]+)` \|", section(5), flags=re.MULTILINE)
    return {(int(status), code) for status, code in rows}


def implemented_errors():
    infos = list(SQLSTATE_ERRORS.values()) + list(HTTP_ERRORS.values())
    infos += [INTERNAL_ERROR, DATABASE_UNAVAILABLE, VALIDATION_ERROR, INVALID_JSON, INVALID_CREDENTIALS,
              SCREENING_STARTED]
    return {(info.status, info.code) for info in infos}


def test_every_error_code_in_the_code_is_documented_and_vice_versa():
    assert documented_errors() == implemented_errors()


def test_the_documented_error_statuses_match_the_database_contract_mapping():
    # UC0xx rows are named in the table; their statuses must be the ones errors.py returns
    documented = documented_errors()
    for sqlstate, info in SQLSTATE_ERRORS.items():
        assert (info.status, info.code) in documented, sqlstate


def test_endpoints_documented_as_existing_exist_with_the_documented_method_and_policy():
    app = create_app("testing")
    from app.security import Policy, route_policies

    rows = re.findall(r"^\| (GET|POST|PUT) \| `([^`]+)` \| (\w+) \|", section(11), flags=re.MULTILINE)
    assert {normalized(path) for _, path, _ in rows} == {
        "/api", "/health", "/health/db",
        "/api/auth/register", "/api/auth/login", "/api/auth/me", "/api/auth/logout",
        "/api/movies", "/api/movies/{id}", "/api/screenings", "/api/screenings/{id}",
        "/api/screenings/{id}/seats",
        "/api/bookings", "/api/bookings/{id}",
        "/api/bookings/{id}/pay", "/api/bookings/{id}/cancel",
        "/api/admin/movies", "/api/admin/movies/{id}",
        "/api/admin/screenings", "/api/admin/screenings/{id}",
        "/api/admin/bookings",
    }
    policies = route_policies(app)
    rules = {(normalized(rule.rule), method): rule.endpoint
             for rule in app.url_map.iter_rules() for method in rule.methods}
    for method, path, policy in rows:
        assert (normalized(path), method) in rules, (method, path)
        assert policies[rules[(normalized(path), method)]] is Policy(policy)


def test_the_application_has_no_endpoint_the_contract_does_not_document():
    app = create_app("testing")
    documented = {normalized(path) for path in re.findall(
        r"^\| (?:GET|POST|PUT) \| `([^`]+)`", section(11), flags=re.MULTILINE)}

    actual = {normalized(rule.rule) for rule in app.url_map.iter_rules()}

    assert actual == documented


def test_endpoints_still_planned_in_section_12_do_not_exist_yet():
    # Section 12 is a plan. When a task implements an endpoint it moves to section 11; until
    # then the route must not exist. With every Phase 4 endpoint implemented the section lists
    # none, so it must say so explicitly instead of the check silently passing.
    app = create_app("testing")
    planned = re.findall(r"`(?:GET|POST|PUT)(?:`/`(?:GET|POST|PUT))? (/api/[^`?\s]+)", section(12))
    if not planned:
        assert "all Phase 4 endpoints implemented" in TEXT.split("\n## 12.", 1)[1].split("\n", 1)[0]
        return
    actual = {re.sub(r"<[^>]+>", "{x}", rule.rule) for rule in app.url_map.iter_rules()}
    normalized = {re.sub(r"\{[^}]+\}", "{x}", path) for path in planned}

    assert not (normalized & actual)


def test_documented_ports_and_variables_match_the_configuration_names():
    from app.config import DevelopmentConfig

    for name in ("CORS_ALLOWED_ORIGINS", "AUTH_TOKEN_MAX_AGE_SECONDS"):
        assert name in TEXT
    config = DevelopmentConfig({"SECRET_KEY": "a-secret-key-with-enough-length", "DB_NAME": "x", "DB_USER": "y"})
    assert config.AUTH_TOKEN_MAX_AGE_SECONDS == 28800 and "28800" in TEXT
    assert config.MAX_CONTENT_LENGTH == 64 * 1024 and "64 KiB" in TEXT
    for variable in ("FRONTEND_HOST", "FRONTEND_PORT", "API_BASE_URL"):
        assert variable in TEXT
