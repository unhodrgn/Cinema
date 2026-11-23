"""T1: route policies, Bearer tokens and the fail-closed guard (no login workflow yet)."""

from types import SimpleNamespace

import itsdangerous.timed
import pytest
from flask import g, jsonify

from app import create_app, security
from app.config import ConfigError, DevelopmentConfig
from app.security import Policy, policy

USERS = {
    1: {"user_id": 1, "username": "customer", "role": "CUSTOMER"},
    2: {"user_id": 2, "username": "admin", "role": "ADMIN"},
}


@pytest.fixture
def app():
    app = create_app("testing")

    @app.get("/t/public")
    @policy(Policy.PUBLIC)
    def public():
        return jsonify(who="anyone")

    @app.get("/t/customer")
    @policy(Policy.CUSTOMER)
    def customer():
        return jsonify(user=g.current_user["username"])

    @app.get("/t/admin")
    @policy(Policy.ADMIN)
    def admin():
        return jsonify(user=g.current_user["username"])

    return app


@pytest.fixture
def with_loader(app):
    users = {key: dict(value) for key, value in USERS.items()}
    security.set_user_loader(app, lambda user_id: users.get(user_id))
    return users


def token_for(app, user_id):
    with app.app_context():
        return security.issue_token(user_id)[0]


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


# --- route policy registry --------------------------------------------------------------


def test_every_route_of_the_real_application_declares_a_policy():
    app = create_app("testing")

    assert security.unclassified_routes(app) == []
    policies = security.route_policies(app)
    assert policies["health.health"] is Policy.PUBLIC
    assert policies["health.health_db"] is Policy.PUBLIC
    assert policies["api.service_info"] is Policy.PUBLIC
    assert all(isinstance(level, Policy) for level in policies.values())


def test_a_route_without_a_policy_is_reported_and_blocks_startup_checks(app):
    @app.get("/t/forgotten")
    def forgotten():
        return "x"

    assert security.unclassified_routes(app) == ["/t/forgotten -> forgotten"]
    with pytest.raises(RuntimeError, match="/t/forgotten"):
        security.check_route_policies(app)


def test_classify_declares_policies_for_views_that_cannot_be_decorated(app):
    @app.get("/t/legacy")
    def legacy():
        return "x"

    security.classify(app, {"legacy": Policy.PUBLIC})

    assert security.unclassified_routes(app) == []
    with pytest.raises(TypeError):
        security.classify(app, {"legacy": "public"})


def test_the_policy_decorator_needs_a_policy_value():
    with pytest.raises(TypeError):
        policy("public")


def test_public_routes_need_no_token(app):
    assert app.test_client().get("/t/public").get_json() == {"who": "anyone"}


# --- the guard --------------------------------------------------------------------------


def test_protected_routes_fail_closed_until_a_user_loader_exists(app):
    # Since T2 create_app registers the database loader; without any loader (removed here)
    # the guard must still refuse everybody.
    security.set_user_loader(app, None)
    token = token_for(app, 1)

    for path in ("/t/customer", "/t/admin"):
        response = app.test_client().get(path, headers=bearer(token))
        assert response.status_code == 401
        assert response.get_json()["error"]["code"] == "unauthorized"


def test_the_real_application_registers_the_database_user_loader():
    from app import auth

    app = create_app("testing")

    assert app.extensions["cinema.user_loader"] is auth.load_user


def test_authenticated_policy_accepts_any_role_but_still_needs_a_token(app, with_loader):
    @app.get("/t/any")
    @policy(Policy.AUTHENTICATED)
    def any_role():
        return jsonify(user=g.current_user["username"])

    client = app.test_client()

    assert client.get("/t/any").status_code == 401
    assert client.get("/t/any", headers=bearer(token_for(app, 1))).get_json() == {"user": "customer"}
    assert client.get("/t/any", headers=bearer(token_for(app, 2))).get_json() == {"user": "admin"}


def test_a_missing_token_is_a_401_with_a_bearer_challenge(app, with_loader):
    response = app.test_client().get("/t/customer")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.get_json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(
    "header", ["Basic abc", "Bearer", "Bearer a b", "Token abc", "Bearer <script>", "Bearer " + "a" * 600]
)
def test_malformed_authorization_headers_are_unauthorized(app, with_loader, header):
    response = app.test_client().get("/t/customer", headers={"Authorization": header})

    assert response.status_code == 401


def test_an_invalid_token_is_a_401(app, with_loader):
    response = app.test_client().get("/t/customer", headers=bearer("not.a.token"))

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == 'Bearer error="invalid_token"'


def test_the_right_role_gets_through_and_the_user_comes_from_the_loader(app, with_loader):
    customer = app.test_client().get("/t/customer", headers=bearer(token_for(app, 1)))
    admin = app.test_client().get("/t/admin", headers=bearer(token_for(app, 2)))

    assert customer.get_json() == {"user": "customer"}
    assert admin.get_json() == {"user": "admin"}


def test_the_wrong_role_is_a_403_in_both_directions(app, with_loader):
    client = app.test_client()

    as_customer = client.get("/t/admin", headers=bearer(token_for(app, 1)))
    as_admin = client.get("/t/customer", headers=bearer(token_for(app, 2)))  # B03: ADMIN is not a customer

    for response in (as_customer, as_admin):
        assert response.status_code == 403
        assert response.get_json()["error"]["code"] == "forbidden"


def test_the_role_is_read_at_request_time_not_from_the_token(app, with_loader):
    token = token_for(app, 1)
    client = app.test_client()
    assert client.get("/t/customer", headers=bearer(token)).status_code == 200

    with_loader[1]["role"] = "ADMIN"  # the account's role changes after the token was issued

    assert client.get("/t/customer", headers=bearer(token)).status_code == 403
    assert client.get("/t/admin", headers=bearer(token)).status_code == 200


def test_a_token_for_a_deleted_or_unknown_account_is_unauthorized(app, with_loader):
    token = token_for(app, 1)
    del with_loader[1]

    assert app.test_client().get("/t/customer", headers=bearer(token)).status_code == 401


def test_a_token_is_not_accepted_in_the_query_string_or_a_cookie(app, with_loader):
    token = token_for(app, 1)
    client = app.test_client()

    assert client.get(f"/t/customer?token={token}").status_code == 401
    client.set_cookie("token", token)
    assert client.get("/t/customer").status_code == 401


# --- tokens -----------------------------------------------------------------------------


def test_a_token_round_trips_and_reports_its_lifetime(app):
    with app.app_context():
        token, expires_in = security.issue_token(42)
        assert security.verify_token(token) == 42
    assert expires_in == app.config["AUTH_TOKEN_MAX_AGE_SECONDS"] == 8 * 3600


def test_a_token_contains_no_role_or_username(app):
    token = token_for(app, 7)

    import base64, json

    payload = token.split(".")[0]
    decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    assert decoded == {"uid": 7}


def test_a_tampered_token_is_rejected(app):
    token = token_for(app, 1)
    head, _, signature = token.rpartition(".")
    flipped = head + "." + "A" * len(signature)  # whole signature replaced; one flipped char can decode unchanged
    forged_payload = token_for(app, 2).split(".")[0] + "." + ".".join(token.split(".")[1:])

    with app.app_context():
        assert security.verify_token(flipped) is None
        assert security.verify_token(forged_payload) is None
        assert security.verify_token(token + "x") is None


def test_a_token_signed_with_another_secret_is_rejected(app):
    other = create_app("testing", {"SECRET_KEY": "another-secret-key-of-enough-length"})
    foreign = token_for(other, 1)

    with app.app_context():
        assert security.verify_token(foreign) is None


def test_the_token_cannot_be_reused_as_a_different_kind_of_signature(app):
    from itsdangerous import URLSafeTimedSerializer

    other_salt = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="something-else").dumps({"uid": 1})

    with app.app_context():
        assert security.verify_token(other_salt) is None


def test_a_token_expires_after_the_configured_lifetime(monkeypatch):
    app = create_app("testing", {"AUTH_TOKEN_MAX_AGE_SECONDS": 120})
    token = token_for(app, 1)
    real_time = itsdangerous.timed.time.time()

    for offset, valid in ((60, True), (119, True), (125, False), (3600, False)):
        monkeypatch.setattr(itsdangerous.timed, "time", SimpleNamespace(time=lambda o=offset: real_time + o))
        with app.app_context():
            assert (security.verify_token(token) == 1) is valid, offset


@pytest.mark.parametrize("payload", [{"uid": "1"}, {"uid": True}, {"uid": 0}, {"uid": -3}, {"role": "ADMIN"}, [1], "1"])
def test_tokens_with_an_unexpected_payload_are_rejected(app, payload):
    from itsdangerous import URLSafeTimedSerializer

    with app.app_context():
        signed = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt=security.TOKEN_SALT).dumps(payload)
        assert security.verify_token(signed) is None


@pytest.mark.parametrize("user_id", [0, -1, True, "1", None, 1.5])
def test_issue_token_needs_a_positive_integer_user_id(app, user_id):
    with app.app_context():
        with pytest.raises(ValueError):
            security.issue_token(user_id)


@pytest.mark.parametrize("value", [None, "", " ", 5, object()])
def test_verify_token_rejects_non_tokens(app, value):
    with app.app_context():
        assert security.verify_token(value) is None


# --- configuration ----------------------------------------------------------------------

ENV = {"SECRET_KEY": "a-secret-key-with-enough-length", "DB_NAME": "x", "DB_USER": "y"}


def test_the_token_lifetime_is_configurable_with_safe_bounds():
    assert DevelopmentConfig(ENV).AUTH_TOKEN_MAX_AGE_SECONDS == 28800
    assert DevelopmentConfig(dict(ENV, AUTH_TOKEN_MAX_AGE_SECONDS="3600")).AUTH_TOKEN_MAX_AGE_SECONDS == 3600
    for bad in ("59", "2592001", "abc", "-5", "1.5"):
        with pytest.raises(ConfigError, match="AUTH_TOKEN_MAX_AGE_SECONDS"):
            DevelopmentConfig(dict(ENV, AUTH_TOKEN_MAX_AGE_SECONDS=bad))


def test_the_request_size_limit_is_set():
    assert DevelopmentConfig(ENV).MAX_CONTENT_LENGTH == 64 * 1024
