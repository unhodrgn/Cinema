"""Every route against every kind of caller, generated from the route-policy registry.

Each route declares a policy (``app.security``). This test derives what anonymous callers,
customers and administrators must get from that declaration alone, so any route added by a
later task is checked automatically. Since the guard runs before the view, a dummy id is
enough: a forbidden caller must be refused (401/403) before anything else happens, and an
allowed one must get past the guard (anything but 401/403; 404/400 are fine).

Needs a disposable PostgreSQL (explicit TEST_DB_PORT): the guard reads the account.
"""

import re
import uuid

import pytest

import disposable_db
from app import create_app
from app.core import passwords, security
from app.core.security import Policy
from helpers import ApiClient

HASH = passwords.hash_password("matrix password")
METHODS = ("GET", "POST", "PUT", "DELETE")


@pytest.fixture(scope="module")
def matrix_db(cinema_template_db):
    with disposable_db.clone_database(cinema_template_db) as clone:
        yield clone


@pytest.fixture(scope="module")
def app(matrix_db):
    return create_app("testing", matrix_db.app_config())


@pytest.fixture(scope="module")
def tokens(app, matrix_db):
    connection = matrix_db.connect()
    result = {}
    try:
        for role in ("CUSTOMER", "ADMIN"):
            with connection.cursor() as cur:
                cur.execute("INSERT INTO users(username, password_hash, role) VALUES (%s, %s, %s) RETURNING user_id",
                            (f"matrix_{role.lower()}_{uuid.uuid4().hex[:6]}", HASH, role))
                user_id = cur.fetchone()[0]
            connection.commit()
            with app.app_context():
                result[role] = security.issue_token(user_id)[0]
    finally:
        connection.close()
    return result


def routes(app):
    policies = security.route_policies(app)
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: (r.rule, r.endpoint)):
        for method in METHODS:
            if method in rule.methods:
                yield rule, method, policies[rule.endpoint]


def concrete(rule, method):
    sample_id = "2147483647" if method == "DELETE" else "1"
    return re.sub(r"<[^>]+>", sample_id, rule.rule)


def cases(app_factory=None):
    app = create_app("testing")  # collection needs no database
    return [pytest.param(rule.rule, method, policy, id=f"{method} {rule.rule}")
            for rule, method, policy in routes(app)]


EXPECTED_STATUS_CLASS = {
    # policy -> (anonymous, customer, admin): True = must be refused with the given code
    Policy.PUBLIC: (None, None, None),
    Policy.AUTHENTICATED: (401, None, None),
    Policy.CUSTOMER: (401, None, 403),
    Policy.ADMIN: (401, 403, None),
}


@pytest.mark.parametrize("rule_text, method, policy", cases())
def test_every_route_gives_each_caller_what_its_policy_says(app, tokens, rule_text, method, policy):
    rule = next(r for r in app.url_map.iter_rules() if r.rule == rule_text and method in r.methods)
    path = concrete(rule, method)
    expected = EXPECTED_STATUS_CLASS[policy]
    callers = (
        ("anonymous", ApiClient(app.test_client())),
        ("customer", ApiClient(app.test_client()).set_token(tokens["CUSTOMER"])),
        ("admin", ApiClient(app.test_client()).set_token(tokens["ADMIN"])),
    )
    for (name, client), refused in zip(callers, expected):
        response = client.request(method, path, json={} if method != "GET" else None)
        if refused is not None:
            assert response.status_code == refused, (name, method, rule_text, response.status_code)
            assert response.mimetype == "application/json"
            assert response.get_json()["error"]["code"] in {"unauthorized", "forbidden"}
            if refused == 401:
                assert response.headers["WWW-Authenticate"].startswith("Bearer")
        else:
            assert response.status_code not in (401, 403), (name, method, rule_text, response.status_code)
        assert "Set-Cookie" not in response.headers


def test_the_matrix_covers_every_route_of_the_application(app):
    covered = {rule.rule for rule, _, _ in routes(app)}

    assert covered == {rule.rule for rule in app.url_map.iter_rules()}
    assert {policy for _, _, policy in routes(app)} >= {Policy.PUBLIC, Policy.AUTHENTICATED}


def test_no_route_accepts_a_method_the_api_does_not_use(app):
    rules = list(app.url_map.iter_rules())
    assert {rule.rule for rule in rules if "DELETE" in rule.methods} == {
        "/api/admin/movies/<int:movie_id>",
        "/api/admin/screenings/<int:showtime_id>",
    }
    assert not any("PATCH" in rule.methods for rule in rules)
