"""T1: the JSON-only API foundation (errors, serialization, request body, no pages)."""

import datetime as dt
import uuid
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from flask import abort, jsonify, make_response, render_template
from jinja2 import TemplateNotFound

from app import create_app
from app.api import json_body
from app.errors import UNAUTHORIZED, AppError, ValidationError

SEOUL = ZoneInfo("Asia/Seoul")
HTML_MARKERS = ("<!doctype", "<html", "<title", "</p>")


@pytest.fixture
def app():
    app = create_app("testing")

    @app.get("/t/values")
    def values():
        return jsonify(
            starts_at=dt.datetime(2026, 11, 25, 19, 0, tzinfo=SEOUL),
            on=dt.date(2026, 11, 25),
            price=Decimal("12000.00"),
            small=Decimal("0.50"),
            big=Decimal("1E+3"),
            id=uuid.UUID(int=1),
        )

    @app.get("/t/naive")
    def naive():
        return jsonify(at=dt.datetime(2026, 11, 25, 19, 0))

    @app.post("/t/body")
    def body():
        return jsonify(received=json_body())

    @app.get("/t/invalid")
    def invalid():
        raise ValidationError({"title": "Title is required."})

    @app.get("/t/unauthorized")
    def unauthorized():
        raise AppError(UNAUTHORIZED, headers={"WWW-Authenticate": "Bearer"})

    @app.get("/t/abort/<int:status>")
    def aborting(status):
        abort(status)

    @app.get("/t/abort-response")
    def abort_response():
        abort(make_response("custom", 418))

    @app.get("/t/slash/")
    def slash():
        return "ok"

    @app.get("/t/render")
    def render():
        return render_template("anything.html")

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def assert_json_error(response, status, code, message=None):
    assert response.status_code == status
    assert response.mimetype == "application/json"
    body = response.get_json()
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    if message is not None:
        assert body["error"]["message"] == message
    text = response.get_data(as_text=True).lower()
    assert not any(marker in text for marker in HTML_MARKERS)
    return body


# --- HTTP errors become the JSON envelope -----------------------------------------------


def test_unknown_path_is_a_json_404(client):
    response = client.get("/no/such/page")

    body = assert_json_error(response, 404, "not_found", "The requested resource was not found.")
    assert set(body["error"]) == {"code", "message"}
    assert response.headers["Cache-Control"] == "no-store"


def test_wrong_method_is_a_json_405_that_keeps_the_allow_header(client):
    response = client.post("/health")

    assert_json_error(response, 405, "method_not_allowed")
    assert set(h.strip() for h in response.headers["Allow"].split(",")) >= {"GET", "HEAD", "OPTIONS"}


def test_other_abort_statuses_use_fixed_messages(client):
    assert_json_error(client.get("/t/abort/400"), 400, "bad_request")
    assert_json_error(client.get("/t/abort/403"), 403, "forbidden")
    assert_json_error(client.get("/t/abort/413"), 413, "payload_too_large")
    assert_json_error(client.get("/t/abort/422"), 422, "http_error")
    body = assert_json_error(client.get("/t/abort/503"), 503, "server_error")
    assert body["error"]["message"] == "Something went wrong on our side. Please try again later."


def test_http_error_text_from_werkzeug_is_never_echoed(client):
    response = client.get("/t/abort/404")

    text = response.get_data(as_text=True)
    assert "Not Found" not in text
    assert "requested URL" not in text  # Werkzeug's own description text


def test_an_aborted_response_object_is_returned_unchanged(client):
    response = client.get("/t/abort-response")

    assert response.status_code == 418
    assert response.get_data(as_text=True) == "custom"


def test_trailing_slash_redirects_are_not_converted_to_errors(client):
    response = client.get("/t/slash", follow_redirects=False)

    assert response.status_code == 308
    assert response.headers["Location"].endswith("/t/slash/")


def test_app_error_headers_reach_the_response(client):
    response = client.get("/t/unauthorized")

    assert_json_error(response, 401, "unauthorized")
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_validation_errors_carry_a_fields_object_and_other_errors_do_not(client):
    response = client.get("/t/invalid")

    body = assert_json_error(response, 400, "validation_error")
    assert body["error"]["fields"] == {"title": "Title is required."}
    assert "fields" not in client.get("/no/such/page").get_json()["error"]


def test_existing_database_errors_keep_their_exact_shape(client):
    # Phase 3 contract: nothing but code and message.
    assert client.get("/health").get_json() == {"status": "ok"}


# --- serialization ----------------------------------------------------------------------


def test_datetimes_dates_and_money_follow_the_api_contract(client):
    body = client.get("/t/values").get_json()

    assert body["starts_at"] == "2026-11-25T19:00:00+09:00"
    assert body["on"] == "2026-11-25"
    assert body["price"] == "12000.00"
    assert body["small"] == "0.50"
    assert body["big"] == "1000"  # plain notation, never "1E+3"
    assert body["id"] == str(uuid.UUID(int=1))


def test_money_is_a_string_not_a_number(client):
    raw = client.get("/t/values").get_data(as_text=True)

    assert '"price":"12000.00"' in raw.replace(" ", "")


def test_a_naive_datetime_is_refused_instead_of_guessed(client):
    response = client.get("/t/naive")

    assert_json_error(response, 500, "internal_error")


# --- request bodies ---------------------------------------------------------------------


def test_json_body_accepts_a_json_object(client):
    response = client.post("/t/body", json={"a": 1, "名前": "값"})

    assert response.status_code == 200
    assert response.get_json() == {"received": {"a": 1, "名前": "값"}}


def test_json_body_charset_parameter_is_accepted(client):
    response = client.post(
        "/t/body", data='{"a": 1}', headers={"Content-Type": "application/json; charset=utf-8"}
    )

    assert response.status_code == 200


@pytest.mark.parametrize("content_type", ["text/plain", "application/x-www-form-urlencoded", None])
def test_json_body_requires_the_json_content_type(client, content_type):
    headers = {"Content-Type": content_type} if content_type else {}
    response = client.post("/t/body", data='{"a": 1}', headers=headers)

    assert_json_error(response, 415, "unsupported_media_type")


@pytest.mark.parametrize("payload", ["", "{", "not json", "null", "[1, 2]", '"text"', "42"])
def test_json_body_rejects_malformed_or_non_object_bodies(client, payload):
    response = client.post("/t/body", data=payload, headers={"Content-Type": "application/json"})

    assert_json_error(response, 400, "invalid_json")


def test_json_body_reports_oversized_requests_as_413(client, app):
    limit = app.config["MAX_CONTENT_LENGTH"]
    response = client.post(
        "/t/body", data=b"{" + b" " * (limit + 10) + b"}", headers={"Content-Type": "application/json"}
    )

    assert_json_error(response, 413, "payload_too_large")


# --- no pages, no static files ----------------------------------------------------------


def test_the_backend_has_no_static_endpoint_and_no_template_loader(app):
    assert "static" not in app.view_functions
    assert not any(rule.rule.startswith("/static") for rule in app.url_map.iter_rules())
    assert app.static_folder is None
    assert app.jinja_loader is None


def test_static_paths_are_json_404s(client):
    assert_json_error(client.get("/static/style.css"), 404, "not_found")
    assert_json_error(client.get("/static/../app/config.py"), 404, "not_found")


def test_rendering_a_template_is_impossible(client, app):
    with app.test_request_context():
        with pytest.raises(TemplateNotFound):
            render_template("index.html")


# --- the /api skeleton ------------------------------------------------------------------


def test_api_root_identifies_the_service(client):
    response = client.get("/api")

    assert response.status_code == 200
    assert response.get_json() == {"service": "cinema-reservation-api", "status": "ok"}


def test_unknown_api_paths_are_json_404s(client):
    assert_json_error(client.get("/api/does-not-exist"), 404, "not_found")
    assert_json_error(client.post("/api"), 405, "method_not_allowed")


def test_api_responses_carry_basic_security_headers(client):
    for response in (client.get("/api"), client.get("/health"), client.get("/api/nope")):
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert response.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
        assert response.headers["Cache-Control"] == "no-store"
