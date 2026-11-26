"""Authentication API: register, login, current user, logout (docs/api/api_contract.md).

Business rules (B03 C-01, CM-01, CM-02; D4, D5):

* Registration takes only the account ID (``users.username``) and the password. The role is
  assigned by this code (the column default ``CUSTOMER``); a role in the request is never
  read. Public registration can therefore never create an ADMIN (BR-14).
* Login answers an unknown account and a wrong password with the same status, code and
  message, and spends the time of one real verification either way.
* Logout never fails because nobody is logged in (CM-02): the endpoint is public and, as
  tokens are stateless, has nothing to do on the server.

Passwords, hashes and tokens are never logged and never returned.
"""

import unicodedata

import psycopg2
from flask import Blueprint, g, jsonify

from app.core.body import json_body
from app.core.database import transaction
from app.core.errors import INVALID_CREDENTIALS, SQLSTATE_ERRORS, AppError, ValidationError
from app.core.passwords import (
    PASSWORD_MAX_LENGTH,
    USERNAME_MAX_LENGTH,
    hash_password,
    verify_against_dummy,
    verify_password,
)
from app.core.security import Policy, issue_token, policy
from app.core.username_policy import registration_username
from app.models.user import public_user

bp = Blueprint("auth", __name__, url_prefix="/auth")

_BEARER_CHALLENGE = {"WWW-Authenticate": "Bearer"}


# --- validation ---------------------------------------------------------------------


def normalize_username(value):
    """The historical login lookup: NFKC (full-width letters and compatibility forms become plain
    ones) with leading and trailing whitespace removed. Login then compares it
    ignoring case (``users_username_lower_key``). Non-text values are returned unchanged for
    the validators to reject."""
    return unicodedata.normalize("NFKC", value).strip() if isinstance(value, str) else value


def check_password(value, enforce_length=True):
    """A fixed error message for an unusable password, or None."""
    if value is None or value == "":
        return "Password is required."
    if not isinstance(value, str):
        return "Password must be text."
    if enforce_length and len(value) > PASSWORD_MAX_LENGTH:
        return f"Password must be at most {PASSWORD_MAX_LENGTH} characters."
    return None


def _credential_fields(body, for_registration):
    """``(username, password)`` from a request body, or raise ``ValidationError``.

    Only these two keys are ever read: anything else in the body (a ``role``, a
    ``user_id``, ...) is ignored. For login the password length is not validated here: a
    too-long password simply cannot match (see ``login``).
    """
    raw_username, password = body.get("username"), body.get("password")
    if for_registration:
        username, username_error = registration_username(raw_username)
        problems = {"username": username_error, "password": check_password(password)}
    else:
        username = normalize_username(raw_username)
        problems = {
            "username": "Account ID is required."
            if username is None or (isinstance(username, str) and username.strip() == "")
            else ("Account ID must be text." if not isinstance(username, str) else None),
            "password": check_password(password, enforce_length=False),
        }
    problems = {name: message for name, message in problems.items() if message}
    if problems:
        raise ValidationError(problems)
    return username, password


# --- current-user loader (used by the role guard on every protected request) ----------


def load_user(user_id):
    """The account's CURRENT row from the database, or None if it no longer exists.

    Called for every authenticated request, so a deleted account or a changed role takes
    effect on the very next request. The token only carries the id.
    """
    with transaction() as cur:
        cur.execute("SELECT user_id, username, role FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
    return dict(row) if row is not None else None


# --- endpoints ------------------------------------------------------------------------


@bp.post("/register")
@policy(Policy.PUBLIC)
def register():
    username, password = _credential_fields(json_body(), for_registration=True)
    password_hash = hash_password(password)
    try:
        with transaction() as cur:
            # No role column: the database default (CUSTOMER) applies. The role is never
            # taken from the request.
            cur.execute(
                "INSERT INTO users(username, password_hash) VALUES (%s, %s) "
                "RETURNING user_id, username, role",
                (username, password_hash),
            )
            row = cur.fetchone()
    except psycopg2.errors.UniqueViolation:
        # The only unique constraints besides the generated key are on username (BR: unique
        # account ID, compared ignoring case).
        raise AppError(
            SQLSTATE_ERRORS["23505"], fields={"username": "This account ID is already in use."}
        ) from None
    except psycopg2.errors.CheckViolation as exc:
        if exc.diag.constraint_name != "users_username_format_check":
            raise
        raise ValidationError({"username": "Account ID has an invalid format."}) from None
    return jsonify(user=public_user(row)), 201


@bp.post("/login")
@policy(Policy.PUBLIC)
def login():
    username, password = _credential_fields(json_body(), for_registration=False)

    row = None
    # An account ID that cannot exist (too long, or with a character PostgreSQL cannot
    # store) is treated as unknown instead of being sent to the database.
    if len(username) <= USERNAME_MAX_LENGTH and "\x00" not in username:
        with transaction() as cur:
            cur.execute(
                "SELECT user_id, username, password_hash, role FROM users WHERE lower(username) = lower(%s)",
                (username,),
            )
            row = cur.fetchone()

    if row is not None and len(password) <= PASSWORD_MAX_LENGTH:
        authenticated = verify_password(row["password_hash"], password)
    else:
        authenticated = verify_against_dummy(password[:PASSWORD_MAX_LENGTH])

    if not authenticated:
        # Same answer for "no such account" and "wrong password".
        raise AppError(INVALID_CREDENTIALS, headers=_BEARER_CHALLENGE)

    token, expires_in = issue_token(row["user_id"])
    return jsonify(token=token, token_type="Bearer", expires_in=expires_in, user=public_user(row))


@bp.get("/me")
@policy(Policy.AUTHENTICATED)
def me():
    return jsonify(user=public_user(g.current_user))


@bp.post("/logout")
@policy(Policy.PUBLIC)
def logout():
    # Stateless tokens: there is nothing to revoke on the server, the browser discards the
    # token. Public on purpose: logging out while not logged in is not an error (CM-02).
    return "", 204
