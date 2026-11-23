"""T2: authentication API through real Flask requests against a real PostgreSQL clone.

Covers registration, login, tokens, the role guard (with the account re-read from the
database on every request), CORS on the authentication endpoints and the "nothing secret
leaks" rules. Needs a disposable PostgreSQL (explicit TEST_DB_PORT); skipped otherwise.
"""

import json
import logging
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import itsdangerous.timed
import pytest
from flask import g, jsonify
from itsdangerous import URLSafeTimedSerializer

import disposable_db
from app import create_app, passwords, security
from app.security import Policy, policy
from helpers import ApiClient

FRONTEND = "http://localhost:8080"
EVIL = "http://evil.example"
KNOWN_PASSWORD = "Pa55-word known to the tests"
SEED = (Path(__file__).resolve().parents[1] / "database" / "seed.sql").read_text(encoding="utf-8")

# Computed once: one PBKDF2 hash costs a few hundred milliseconds.
KNOWN_HASH = passwords.hash_password(KNOWN_PASSWORD)


# --- fixtures ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def auth_db(cinema_template_db):
    with disposable_db.clone_database(cinema_template_db) as clone:
        yield clone


def build_app(auth_db, **overrides):
    config = dict(auth_db.app_config(), CORS_ALLOWED_ORIGINS=FRONTEND)
    config.update(overrides)
    return create_app("testing", config)


@pytest.fixture(scope="module")
def app(auth_db):
    app = build_app(auth_db)

    @app.get("/t/customer-only")
    @policy(Policy.CUSTOMER)
    def customer_only():
        return jsonify(user=g.current_user["username"], role=g.current_user["role"])

    @app.get("/t/admin-only")
    @policy(Policy.ADMIN)
    def admin_only():
        return jsonify(user=g.current_user["username"], role=g.current_user["role"])

    return app


@pytest.fixture(scope="module")
def owner(auth_db):
    """An owner connection to the module's database (for setup and for reading the truth)."""
    connection = auth_db.connect()
    yield connection
    connection.close()


@pytest.fixture
def client(app):
    return ApiClient(app.test_client(), origin=FRONTEND)


def unique(prefix="u"):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def make_user(owner, role="CUSTOMER", password_hash=None, username=None):
    """Insert an account directly (fast: known pre-computed hash). Returns (user_id, username)."""
    username = username or unique(role.lower())
    with owner.cursor() as cur:
        cur.execute(
            "INSERT INTO users(username, password_hash, role) VALUES (%s, %s, %s) RETURNING user_id",
            (username, password_hash or KNOWN_HASH, role),
        )
        user_id = cur.fetchone()[0]
    owner.commit()
    return user_id, username


def db_row(owner, username):
    with owner.cursor() as cur:
        cur.execute("SELECT user_id, username, password_hash, role FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
    owner.rollback()
    return row


def count_users(owner, username):
    with owner.cursor() as cur:
        cur.execute("SELECT count(*) FROM users WHERE username = %s", (username,))
        value = cur.fetchone()[0]
    owner.rollback()
    return value


def token_for(app, user_id):
    with app.app_context():
        return security.issue_token(user_id)[0]


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def register(client, username, password=KNOWN_PASSWORD, **extra):
    return client.post("/api/auth/register", json={"username": username, "password": password, **extra})


def login(client, username, password=KNOWN_PASSWORD):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def error_of(response):
    return response.get_json()["error"]


# --- registration -----------------------------------------------------------------------


def test_registration_creates_a_customer_and_returns_only_public_fields(client, owner):
    name = unique("alice")

    response = register(client, name)

    assert response.status_code == 201
    body = response.get_json()
    assert set(body) == {"user"}
    assert set(body["user"]) == {"user_id", "username", "role"}
    assert body["user"]["username"] == name and body["user"]["role"] == "CUSTOMER"
    row = db_row(owner, name)
    assert row[3] == "CUSTOMER" and row[0] == body["user"]["user_id"]
    # stored as a one-way salted hash in the seed's method; the password itself is nowhere
    assert row[2].startswith("pbkdf2:sha256:600000$") and KNOWN_PASSWORD not in row[2]
    text = response.get_data(as_text=True)
    assert KNOWN_PASSWORD not in text and row[2] not in text and "password" not in text.lower()
    assert "Set-Cookie" not in response.headers


def test_registration_does_not_log_the_user_in(client):
    response = register(client, unique())

    assert "token" not in response.get_data(as_text=True)


@pytest.mark.parametrize(
    "extra",
    [
        {"role": "ADMIN"},
        {"role": "admin"},
        {"role": ["ADMIN"]},
        {"role": {"name": "ADMIN"}},
        {"user_id": 1, "is_admin": True, "isAdmin": True, "admin": True},
        {"created_at": "2000-01-01T00:00:00+00:00"},
        {"role": "ADMIN", "Role": "ADMIN", "ROLE": "ADMIN"},
    ],
)
def test_a_role_or_any_other_field_in_the_request_is_ignored(client, owner, extra):
    name = unique("sneaky")

    response = register(client, name, **extra)

    assert response.status_code == 201
    assert response.get_json()["user"]["role"] == "CUSTOMER"
    assert db_row(owner, name)[3] == "CUSTOMER"
    assert db_row(owner, name)[0] != 1  # a client-supplied user_id is never used


def test_a_registered_account_can_log_in_and_is_never_an_admin(client):
    name = unique("viaapi")
    register(client, name, role="ADMIN")

    body = login(client, name).get_json()

    assert body["user"]["role"] == "CUSTOMER"


def test_a_duplicate_account_id_is_a_409_and_creates_nothing(client, owner):
    name = unique("dup")
    assert register(client, name).status_code == 201

    response = register(client, name, password="another password")

    assert response.status_code == 409
    assert error_of(response)["code"] == "duplicate_value"
    assert error_of(response)["fields"] == {"username": "This account ID is already in use."}
    assert count_users(owner, name) == 1
    assert passwords.verify_password(db_row(owner, name)[2], KNOWN_PASSWORD)  # first password intact
    text = response.get_data(as_text=True)
    assert "users_username_key" not in text and "duplicate key" not in text and "INSERT" not in text


def test_the_seeded_account_ids_are_taken(client):
    for name in ("admin_demo", "customer_demo", "customer_demo2"):
        assert register(client, name).status_code == 409


def test_simultaneous_registrations_of_one_account_id_create_exactly_one_account(app, owner):
    name = unique("race")
    barrier = threading.Barrier(6)

    def attempt(_):
        barrier.wait()
        return register(ApiClient(app.test_client()), name).status_code

    with ThreadPoolExecutor(6) as pool:
        statuses = list(pool.map(attempt, range(6)))

    assert sorted(statuses) == [201] + [409] * 5
    assert count_users(owner, name) == 1


@pytest.mark.parametrize(
    "body, field, message",
    [
        ({"password": "x"}, "username", "Account ID is required."),
        ({"username": None, "password": "x"}, "username", "Account ID is required."),
        ({"username": "", "password": "x"}, "username", "Account ID is required."),
        ({"username": "   ", "password": "x"}, "username", "Account ID is required."),
        ({"username": 12, "password": "x"}, "username", "Account ID must be text."),
        ({"username": ["a"], "password": "x"}, "username", "Account ID must be text."),
        ({"username": {"a": 1}, "password": "x"}, "username", "Account ID must be text."),
        ({"username": "a" * 61, "password": "x"}, "username", "Account ID must be at most 60 characters."),
        ({"username": "nul\u0000byte", "password": "x"}, "username", "Account ID must not contain control characters."),
        ({"username": "line\nbreak", "password": "x"}, "username", "Account ID must not contain control characters."),
        ({"username": "tab\there", "password": "x"}, "username", "Account ID must not contain control characters."),
        ({"username": "ok"}, "password", "Password is required."),
        ({"username": "ok", "password": ""}, "password", "Password is required."),
        ({"username": "ok", "password": None}, "password", "Password is required."),
        ({"username": "ok", "password": 123456}, "password", "Password must be text."),
        ({"username": "ok", "password": "p" * 257}, "password", "Password must be at most 256 characters."),
    ],
)
def test_invalid_registrations_report_the_field_and_create_nothing(client, owner, body, field, message):
    if isinstance(body.get("username"), str) and body["username"] == "ok":
        body = dict(body, username=unique("val"))
    response = client.post("/api/auth/register", json=body)

    assert response.status_code == 400
    assert error_of(response)["code"] == "validation_error"
    assert error_of(response)["fields"][field] == message
    text = response.get_data(as_text=True)
    for secret in ("p" * 257, "nul\u0000byte"):
        assert secret not in text
    if isinstance(body.get("username"), str) and field != "username":
        assert count_users(owner, body["username"]) == 0


def test_both_field_problems_are_reported_together(client):
    response = client.post("/api/auth/register", json={})

    assert set(error_of(response)["fields"]) == {"username", "password"}


def test_the_limits_are_inclusive_and_unicode_works(client, owner):
    long_name = "n" * 60
    long_password = "é" * 256
    korean = "홍길동_" + uuid.uuid4().hex[:6]

    for name, password in ((long_name + "", long_password), (korean, "비밀번호-" + "x" * 5)):
        name = name if name != long_name else (uuid.uuid4().hex[:8] + "n" * 52)
        assert register(client, name, password).status_code == 201
        assert login(client, name, password).status_code == 200
        assert db_row(owner, name)[1] == name


def test_special_characters_in_the_account_id_are_data_not_sql(client, owner):
    name = "x'; DROP TABLE users; --" + uuid.uuid4().hex[:6]

    assert register(client, name).status_code == 201
    assert login(client, name).status_code == 200
    assert count_users(owner, name) == 1
    with owner.cursor() as cur:
        cur.execute("SELECT count(*) FROM users")
        assert cur.fetchone()[0] >= 3  # the table is intact
    owner.rollback()


def test_registration_needs_a_json_object(client):
    assert client.post("/api/auth/register", data="username=a&password=b",
                       headers={"Content-Type": "application/x-www-form-urlencoded"}).status_code == 415
    for payload in ("", "{", "[]", '"text"', "null"):
        response = client.post("/api/auth/register", data=payload, headers={"Content-Type": "application/json"})
        assert response.status_code == 400 and error_of(response)["code"] == "invalid_json"


# --- login ------------------------------------------------------------------------------


def test_login_returns_a_token_and_the_public_user(app, client, owner):
    user_id, name = make_user(owner)

    response = login(client, name)

    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {"token", "token_type", "expires_in", "user"}
    assert body["token_type"] == "Bearer" and body["expires_in"] == 28800
    assert body["user"] == {"user_id": user_id, "username": name, "role": "CUSTOMER"}
    with app.app_context():
        assert security.verify_token(body["token"]) == user_id
    assert response.headers["Cache-Control"] == "no-store"
    assert "Set-Cookie" not in response.headers


def test_the_token_contains_only_the_user_id(client, owner):
    user_id, name = make_user(owner, role="ADMIN")
    token = login(client, name).get_json()["token"]

    payload = token.split(".")[0]
    import base64

    decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    assert decoded == {"uid": user_id}


def test_an_admin_logs_in_through_the_same_endpoint(client, owner):
    _, name = make_user(owner, role="ADMIN")

    assert login(client, name).get_json()["user"]["role"] == "ADMIN"


def test_wrong_password_and_unknown_account_look_identical(client, owner):
    _, name = make_user(owner)

    wrong = login(client, name, "not the password")
    unknown = login(client, unique("ghost"), KNOWN_PASSWORD)

    for response in (wrong, unknown):
        assert response.status_code == 401
        assert error_of(response) == {
            "code": "invalid_credentials",
            "message": "The account ID or password is incorrect.",
        }
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert "token" not in response.get_data(as_text=True)
    assert wrong.get_data() == unknown.get_data()  # byte for byte
    assert {k: v for k, v in wrong.headers if k.lower() != "date"} == \
           {k: v for k, v in unknown.headers if k.lower() != "date"}


def test_every_login_failure_verifies_one_password_hash(app, client, owner, monkeypatch):
    _, name = make_user(owner)
    calls = []
    real = passwords.check_password_hash

    def spy(stored, candidate):
        calls.append(stored)
        return real(stored, candidate)

    monkeypatch.setattr(passwords, "check_password_hash", spy)

    login(client, name, "wrong")  # existing account, wrong password
    existing_hash = calls[-1]
    login(client, unique("ghost"), "anything")  # unknown account
    login(client, "g" * 61, "anything")  # cannot exist (too long)
    login(client, "nul\u0000", "anything")  # cannot exist (NUL)
    login(client, name, "p" * 300)  # existing account, over-long password

    assert existing_hash == db_row(owner, name)[2]
    assert len(calls) == 5, "every failed login must cost exactly one hash verification"
    dummy = calls[1]
    assert dummy.startswith("pbkdf2:sha256:600000$") and dummy != existing_hash
    assert calls[2] == calls[3] == calls[4] == dummy  # the same dummy, never the real hash


def test_a_wrong_password_never_authenticates_even_when_it_resembles_the_right_one(client, owner):
    _, name = make_user(owner)

    for candidate in (KNOWN_PASSWORD + " ", KNOWN_PASSWORD.upper(), KNOWN_PASSWORD[:-1], " " + KNOWN_PASSWORD):
        assert login(client, name, candidate).status_code == 401


@pytest.mark.parametrize(
    "body, fields",
    [
        ({}, {"username", "password"}),
        ({"username": "x"}, {"password"}),
        ({"password": "x"}, {"username"}),
        ({"username": "", "password": ""}, {"username", "password"}),
        ({"username": 5, "password": "x"}, {"username"}),
        ({"username": "x", "password": ["y"]}, {"password"}),
    ],
)
def test_login_with_missing_or_malformed_fields_is_a_validation_error(client, body, fields):
    response = client.post("/api/auth/login", json=body)

    assert response.status_code == 400
    assert error_of(response)["code"] == "validation_error"
    assert set(error_of(response)["fields"]) == fields


@pytest.mark.parametrize("username", ["' OR '1'='1", "admin_demo'--", "%", "_", "ADMIN_DEMO", "admin_demo "])
def test_login_does_not_match_account_ids_by_pattern_or_injection(client, username):
    assert login(client, username, "x").status_code == 401


def test_the_seeded_password_hashes_are_verifiable(client):
    hashes = re.findall(r"'(pbkdf2:sha256:600000\$[0-9a-f]+\$[0-9a-f]+)'", SEED)
    assert len(hashes) == 3
    for stored in hashes:
        assert passwords.verify_password(stored, "definitely not the password") is False  # parses, no error
    # Through the API: a seeded account with a wrong password is a clean 401, never a crash
    for name in ("admin_demo", "customer_demo", "customer_demo2"):
        response = login(client, name, "definitely not the password")
        assert response.status_code == 401 and error_of(response)["code"] == "invalid_credentials"


def test_hashes_in_the_seeds_format_and_other_werkzeug_formats_authenticate(client, owner):
    from werkzeug.security import generate_password_hash

    seed_format = generate_password_hash("seed format pw", method="pbkdf2:sha256:600000")
    other_format = generate_password_hash("scrypt pw", method="scrypt:32768:8:1")
    assert seed_format.split("$")[0] == "pbkdf2:sha256:600000" == passwords.PASSWORD_HASH_METHOD
    _, first = make_user(owner, password_hash=seed_format)
    _, second = make_user(owner, password_hash=other_format)

    assert login(client, first, "seed format pw").status_code == 200
    assert login(client, second, "scrypt pw").status_code == 200
    assert login(client, first, "scrypt pw").status_code == 401


def test_a_malformed_stored_hash_cannot_log_in_and_is_not_a_server_error(client, owner):
    for broken in ("", "plaintext-not-a-hash", "unknown-method$salt$hash", "pbkdf2:sha256:abc$s$h"):
        _, name = make_user(owner, password_hash=broken)
        response = login(client, name, "anything")
        assert response.status_code == 401, broken


# --- tokens and /me ---------------------------------------------------------------------


def test_me_returns_the_current_account_for_a_valid_token(app, client, owner):
    user_id, name = make_user(owner)

    response = client.get("/api/auth/me", headers=bearer(token_for(app, user_id)))

    assert response.status_code == 200
    assert response.get_json() == {"user": {"user_id": user_id, "username": name, "role": "CUSTOMER"}}
    assert "password" not in response.get_data(as_text=True).lower()


def test_the_full_flow_register_login_me(client):
    name = unique("flow")
    register(client, name)
    token = login(client, name).get_json()["token"]

    me = client.get("/api/auth/me", headers=bearer(token))

    assert me.status_code == 200 and me.get_json()["user"]["username"] == name


def test_a_missing_token_is_401_with_a_bearer_challenge(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert error_of(response)["code"] == "unauthorized"


@pytest.mark.parametrize(
    "header",
    ["Basic abc", "Bearer", "Bearer ", "Bearer a b", "Token abc", "bearer", "Bearer <script>alert(1)</script>",
     "Bearer " + "a" * 600, "Bearer abc,def", "Bearerabc", "Bearer  abc"],
)
def test_malformed_authorization_headers_are_401(client, header):
    response = client.get("/api/auth/me", headers={"Authorization": header})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"].startswith("Bearer")
    assert header not in response.get_data(as_text=True)


def test_a_tampered_token_is_401_invalid_token(app, client, owner):
    user_id, _ = make_user(owner)
    other_id, _ = make_user(owner)
    token = token_for(app, user_id)
    head, _, signature = token.rpartition(".")
    flipped = head + "." + "A" * len(signature)  # whole signature replaced; one flipped char can decode unchanged
    # another user's payload with this user's signature
    grafted = token_for(app, other_id).split(".")[0] + "." + ".".join(token.split(".")[1:])

    for bad in (flipped, grafted, token + "x", token[:-3], "." + token, "not.a.token"):
        response = client.get("/api/auth/me", headers=bearer(bad))
        assert response.status_code == 401, bad
        assert response.headers["WWW-Authenticate"] == 'Bearer error="invalid_token"'
        assert bad not in response.get_data(as_text=True)


def test_an_expired_token_is_rejected_exactly_after_the_lifetime(app, client, owner, monkeypatch):
    user_id, _ = make_user(owner)
    token = token_for(app, user_id)
    now = itsdangerous.timed.time.time()
    lifetime = app.config["AUTH_TOKEN_MAX_AGE_SECONDS"]

    def at(offset):
        monkeypatch.setattr(itsdangerous.timed, "time", SimpleNamespace(time=lambda: now + offset))
        return client.get("/api/auth/me", headers=bearer(token))

    assert at(60).status_code == 200
    assert at(lifetime - 5).status_code == 200
    expired = at(lifetime + 5)
    assert expired.status_code == 401
    assert expired.headers["WWW-Authenticate"] == 'Bearer error="invalid_token"'
    assert at(10 * lifetime).status_code == 401


def test_the_token_lifetime_comes_from_the_configuration(auth_db, owner):
    short = build_app(auth_db, AUTH_TOKEN_MAX_AGE_SECONDS=120)
    user_id, name = make_user(owner)

    body = login(ApiClient(short.test_client()), name).get_json()

    assert body["expires_in"] == 120


def test_a_token_signed_with_another_secret_is_rejected(auth_db, client, owner):
    foreign_app = build_app(auth_db, SECRET_KEY="another-secret-key-of-enough-length")
    _, name = make_user(owner)
    foreign_token = login(ApiClient(foreign_app.test_client()), name).get_json()["token"]

    own = client.get("/api/auth/me", headers=bearer(foreign_token))

    assert own.status_code == 401
    assert ApiClient(foreign_app.test_client()).get("/api/auth/me", headers=bearer(foreign_token)).status_code == 200


def test_a_token_of_a_deleted_account_stops_working_immediately(app, client, owner):
    user_id, name = make_user(owner)
    token = login(client, name).get_json()["token"]
    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 200

    with owner.cursor() as cur:
        cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    owner.commit()

    response = client.get("/api/auth/me", headers=bearer(token))
    assert response.status_code == 401
    assert client.get("/t/customer-only", headers=bearer(token)).status_code == 401


def test_a_role_change_in_the_database_applies_to_the_next_request(app, client, owner):
    user_id, name = make_user(owner)
    token = login(client, name).get_json()["token"]  # the token is never re-issued below

    def status(path):
        return client.get(path, headers=bearer(token)).status_code

    assert (status("/t/customer-only"), status("/t/admin-only")) == (200, 403)
    assert client.get("/api/auth/me", headers=bearer(token)).get_json()["user"]["role"] == "CUSTOMER"

    with owner.cursor() as cur:
        cur.execute("UPDATE users SET role = 'ADMIN' WHERE user_id = %s", (user_id,))
    owner.commit()

    assert (status("/t/customer-only"), status("/t/admin-only")) == (403, 200)  # ADMIN is not a customer
    assert client.get("/api/auth/me", headers=bearer(token)).get_json()["user"]["role"] == "ADMIN"

    with owner.cursor() as cur:
        cur.execute("UPDATE users SET role = 'CUSTOMER' WHERE user_id = %s", (user_id,))
    owner.commit()

    assert (status("/t/customer-only"), status("/t/admin-only")) == (200, 403)


def test_no_role_can_be_obtained_from_client_controlled_data(app, client, owner):
    user_id, name = make_user(owner)
    secret_key = app.config["SECRET_KEY"]
    # a token with a role claim, even one signed with the real key, grants nothing
    forged = URLSafeTimedSerializer(secret_key, salt=security.TOKEN_SALT).dumps({"uid": user_id, "role": "ADMIN"})
    honest = token_for(app, user_id)

    assert client.get("/t/admin-only", headers=bearer(forged)).status_code == 403
    for attempt in (
        {"headers": {**bearer(honest), "X-Role": "ADMIN", "X-User-Role": "ADMIN", "Role": "ADMIN"}},
        {"headers": bearer(honest), "query_string": {"role": "ADMIN", "admin": "1"}},
    ):
        assert client.get("/t/admin-only", **attempt).status_code == 403
    client.flask.set_cookie("role", "ADMIN")
    client.flask.set_cookie("admin", "1")
    assert client.get("/t/admin-only", headers=bearer(honest)).status_code == 403
    client.flask.delete_cookie("role")
    client.flask.delete_cookie("admin")
    # and a role in the request body of login is not read either
    assert login_with_role(client, name).get_json()["user"]["role"] == "CUSTOMER"


def login_with_role(client, name):
    return client.post("/api/auth/login", json={"username": name, "password": KNOWN_PASSWORD, "role": "ADMIN"})


def test_a_token_is_only_accepted_in_the_authorization_header(app, client, owner):
    user_id, _ = make_user(owner)
    token = token_for(app, user_id)

    assert client.get(f"/api/auth/me?token={token}").status_code == 401
    assert client.get(f"/api/auth/me?access_token={token}").status_code == 401
    client.flask.set_cookie("token", token)
    client.flask.set_cookie("session", token)
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/logout", json={"token": token}).status_code == 204


# --- authorization matrix ---------------------------------------------------------------

MATRIX = [
    # path,              anonymous, customer, admin
    ("/api/auth/me",     401,       200,      200),
    ("/t/customer-only", 401,       200,      403),
    ("/t/admin-only",    401,       403,      200),
]


@pytest.mark.parametrize("path, anonymous, customer, admin", MATRIX)
def test_authorization_matrix(app, client, owner, path, anonymous, customer, admin):
    customer_id, _ = make_user(owner, role="CUSTOMER")
    admin_id, _ = make_user(owner, role="ADMIN")

    assert client.get(path).status_code == anonymous
    assert client.get(path, headers=bearer(token_for(app, customer_id))).status_code == customer
    assert client.get(path, headers=bearer(token_for(app, admin_id))).status_code == admin


def test_the_authentication_routes_declare_their_policies(app):
    policies = security.route_policies(app)

    assert policies["api.auth.register"] is Policy.PUBLIC
    assert policies["api.auth.login"] is Policy.PUBLIC
    assert policies["api.auth.logout"] is Policy.PUBLIC
    assert policies["api.auth.me"] is Policy.AUTHENTICATED


# --- logout -----------------------------------------------------------------------------


def test_logout_without_being_logged_in_is_not_an_error(client):
    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    assert response.get_data() == b""


def test_logout_with_a_valid_expired_or_garbage_token_is_204(app, client, owner):
    user_id, _ = make_user(owner)

    for headers in (bearer(token_for(app, user_id)), bearer("garbage"), {"Authorization": "nonsense"}):
        assert client.post("/api/auth/logout", headers=headers).status_code == 204


def test_logout_is_stateless_so_a_stolen_token_works_until_it_expires(app, client, owner):
    # The documented limitation (API contract, section 6): nothing is revoked on the server.
    user_id, _ = make_user(owner)
    token = token_for(app, user_id)

    assert client.post("/api/auth/logout", headers=bearer(token)).status_code == 204

    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 200


def test_authentication_endpoints_reject_the_wrong_method(client):
    assert client.get("/api/auth/login").status_code == 405
    assert client.get("/api/auth/register").status_code == 405
    assert client.get("/api/auth/logout").status_code == 405
    assert client.post("/api/auth/me").status_code == 405
    assert client.put("/api/auth/login", json={}).status_code == 405


# --- CORS on the authentication endpoints -----------------------------------------------


def preflight(client, origin, path, method="POST", headers="content-type, authorization"):
    return client.options(path, headers={
        "Origin": origin, "Access-Control-Request-Method": method, "Access-Control-Request-Headers": headers})


@pytest.mark.parametrize("path, method", [("/api/auth/login", "POST"), ("/api/auth/register", "POST"),
                                           ("/api/auth/logout", "POST"), ("/api/auth/me", "GET")])
def test_the_frontend_origin_may_call_each_authentication_endpoint(client, path, method):
    response = preflight(client, FRONTEND, path, method)

    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == FRONTEND
    assert response.headers["Access-Control-Allow-Headers"] == "Authorization, Content-Type"
    assert method in response.headers["Access-Control-Allow-Methods"]
    assert "Access-Control-Allow-Credentials" not in response.headers


@pytest.mark.parametrize("path, method", [("/api/auth/login", "POST"), ("/api/auth/register", "POST"),
                                           ("/api/auth/me", "GET"), ("/api/auth/logout", "POST")])
def test_other_origins_get_no_permission_not_even_for_the_authorization_header(client, path, method):
    for origin in (EVIL, "http://localhost:8081", "https://localhost:8080", "null"):
        response = preflight(client, origin, path, method)
        assert "Access-Control-Allow-Origin" not in response.headers, origin
        assert "Access-Control-Allow-Headers" not in response.headers, origin
        assert response.status_code != 204


def test_preflight_cannot_ask_for_cookie_or_unlisted_headers(client):
    for requested in ("cookie", "x-csrf-token", "authorization, x-custom"):
        response = preflight(client, FRONTEND, "/api/auth/login", "POST", requested)
        assert "Access-Control-Allow-Origin" not in response.headers


def test_real_responses_carry_the_origin_for_the_frontend_only(app, client, owner):
    user_id, name = make_user(owner)
    token = login(client, name).get_json()["token"]

    ok = client.post("/api/auth/login", json={"username": name, "password": KNOWN_PASSWORD})
    failed = client.post("/api/auth/login", json={"username": name, "password": "wrong"})  # 401 stays readable
    invalid = client.post("/api/auth/register", json={})  # 400 stays readable
    me = client.get("/api/auth/me", headers=bearer(token))
    anonymous_me = client.get("/api/auth/me")

    for response in (ok, failed, invalid, me, anonymous_me):
        assert response.headers["Access-Control-Allow-Origin"] == FRONTEND
        assert "Origin" in response.headers["Vary"]
        assert "Access-Control-Allow-Credentials" not in response.headers
        assert response.headers["Access-Control-Allow-Origin"] != "*"
    foreign = ApiClient(app.test_client(), origin=EVIL)
    for response in (foreign.post("/api/auth/login", json={"username": name, "password": "x"}),
                     foreign.get("/api/auth/me", headers=bearer(token))):
        assert "Access-Control-Allow-Origin" not in response.headers


def test_authentication_never_relies_on_cookies(client, owner):
    _, name = make_user(owner)

    responses = [register(client, unique()), login(client, name), login(client, name, "bad"),
                 client.get("/api/auth/me"), client.post("/api/auth/logout")]

    assert all("Set-Cookie" not in response.headers for response in responses)
    # a cookie sent by a browser does not authenticate
    token = login(client, name).get_json()["token"]
    client.flask.set_cookie("Authorization", f"Bearer {token}")
    assert client.get("/api/auth/me").status_code == 401


# --- nothing secret leaks ---------------------------------------------------------------


def test_passwords_hashes_and_tokens_never_appear_in_logs_or_error_bodies(app, client, owner, caplog):
    secret_password = "S3cr3t-Marker-9f2c-do-not-log"
    caplog.set_level(logging.DEBUG)
    name = unique("quiet")
    registered = register(client, name, secret_password)
    stored_hash = db_row(owner, name)[2]
    good = login(client, name, secret_password)
    token = good.get_json()["token"]
    bad = login(client, name, secret_password + "x")
    duplicate = register(client, name, secret_password)
    me = client.get("/api/auth/me", headers=bearer(token))
    tampered = client.get("/api/auth/me", headers=bearer(token + "x"))
    garbage_body = client.post("/api/auth/login", data="{" + secret_password, headers={"Content-Type": "application/json"})

    for secret in (secret_password, stored_hash, token):
        assert secret not in caplog.text
        for response in (registered, bad, duplicate, me, tampered, garbage_body):
            assert secret not in response.get_data(as_text=True)
    assert token in good.get_data(as_text=True)  # the one place a token is meant to appear
    assert stored_hash not in good.get_data(as_text=True)


def test_database_errors_in_authentication_are_sanitised(auth_db, monkeypatch):
    unreachable = create_app("testing", dict(auth_db.app_config(), DB_PORT=1, DB_CONNECT_TIMEOUT=1,
                                             CORS_ALLOWED_ORIGINS=FRONTEND))
    client = ApiClient(unreachable.test_client(), origin=FRONTEND)

    responses = [login(client, "x"), register(client, unique()),
                 client.get("/api/auth/me", headers=bearer(token_for(unreachable, 5)))]

    for response in responses:
        assert response.status_code == 503
        assert error_of(response)["code"] == "database_unavailable"
        text = response.get_data(as_text=True)
        assert "127.0.0.1" not in text and auth_db.name not in text
        assert response.headers["Access-Control-Allow-Origin"] == FRONTEND


def test_the_public_user_never_contains_the_password_hash():
    from app.auth import public_user

    row = {"user_id": 1, "username": "a", "role": "CUSTOMER", "password_hash": "pbkdf2:sha256:1$a$b"}

    assert public_user(row) == {"user_id": 1, "username": "a", "role": "CUSTOMER"}
