"""Shared security infrastructure: route policies, Bearer tokens, response headers.

This module is the foundation that T2 (authentication) builds on. It contains no login,
registration or logout workflow and does not query the database.

Route policies
    Every route declares who may call it (``Policy.PUBLIC``, ``CUSTOMER`` or ``ADMIN``).
    ``create_app`` refuses to start while any route is unclassified, so a new endpoint can
    never be reachable by accident. ``CUSTOMER`` and ``ADMIN`` routes are guarded by the
    ``policy`` decorator: 401 without a valid token, 403 for the wrong role. The guard
    **fails closed**: until a user loader is registered (T2) every protected route answers
    401. Roles are never read from the token: the loader returns the current database row.

Tokens
    ``issue_token`` / ``verify_token`` sign ``{"uid": <user id>}`` with the application's
    ``SECRET_KEY`` (itsdangerous, already a Flask dependency) and enforce the configured
    lifetime. Tokens are stateless: logout discards them in the client, they cannot be
    revoked on the server (documented limitation, revised Phase 4 plan, section 4).
"""

import enum
import functools
import logging
import re

from flask import current_app, g, request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from .errors import FORBIDDEN, UNAUTHORIZED, AppError

logger = logging.getLogger(__name__)

TOKEN_SALT = "cinema.auth.token.v1"
MAX_TOKEN_LENGTH = 512

_POLICY_OVERRIDES_KEY = "cinema.route_policies"
_USER_LOADER_KEY = "cinema.user_loader"

# itsdangerous URL-safe tokens use letters, digits, '-', '_' and '.' only.
_BEARER_PATTERN = re.compile(r"^Bearer ([A-Za-z0-9_\-.]+)$", re.IGNORECASE)


class Policy(str, enum.Enum):
    PUBLIC = "public"  # anyone, no token
    AUTHENTICATED = "authenticated"  # any logged-in account, whatever its role
    CUSTOMER = "customer"  # a logged-in account with role CUSTOMER
    ADMIN = "admin"  # a logged-in account with role ADMIN


# --- route policy registry ------------------------------------------------------------


def policy(level):
    """Declare a route's policy and, for CUSTOMER and ADMIN, enforce it.

    Use directly under the route decorator::

        @bp.get("/bookings")
        @policy(Policy.CUSTOMER)
        def list_bookings(): ...
    """
    if not isinstance(level, Policy):
        raise TypeError("policy() needs a Policy value")

    def decorator(view):
        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            if level is not Policy.PUBLIC:
                _authenticate(level)
            return view(*args, **kwargs)

        wrapper.route_policy = level
        return wrapper

    return decorator


def classify(app, endpoints):
    """Declare policies for views that cannot carry the decorator (``{endpoint: Policy}``)."""
    overrides = app.extensions.setdefault(_POLICY_OVERRIDES_KEY, {})
    for endpoint, level in endpoints.items():
        if not isinstance(level, Policy):
            raise TypeError(f"{endpoint}: policy must be a Policy value")
        overrides[endpoint] = level


def route_policies(app):
    """``{endpoint: Policy or None}`` for every route of the application."""
    overrides = app.extensions.get(_POLICY_OVERRIDES_KEY, {})
    result = {}
    for rule in app.url_map.iter_rules():
        view = app.view_functions.get(rule.endpoint)
        result[rule.endpoint] = overrides.get(rule.endpoint) or getattr(view, "route_policy", None)
    return result


def unclassified_routes(app):
    """Sorted ``"<rule> -> <endpoint>"`` for every route that declares no policy."""
    declared = route_policies(app)
    return sorted(
        f"{rule.rule} -> {rule.endpoint}"
        for rule in app.url_map.iter_rules()
        if declared[rule.endpoint] is None
    )


def check_route_policies(app):
    """Raise ``RuntimeError`` if any route is unclassified (called by ``create_app``)."""
    missing = unclassified_routes(app)
    if missing:
        raise RuntimeError(
            "every route must declare a policy (public, customer or admin); missing:\n  "
            + "\n  ".join(missing)
        )


# --- tokens ---------------------------------------------------------------------------


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=TOKEN_SALT)


def issue_token(user_id):
    """``(token, expires_in_seconds)`` for ``user_id``. Carries no role and no username."""
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id must be a positive integer")
    token = _serializer().dumps({"uid": user_id})
    return token, current_app.config["AUTH_TOKEN_MAX_AGE_SECONDS"]


def verify_token(token):
    """The user id inside a valid, unexpired token, or None (tampered, expired, foreign)."""
    if not isinstance(token, str) or not token or len(token) > MAX_TOKEN_LENGTH:
        return None
    try:
        payload = _serializer().loads(
            token, max_age=current_app.config["AUTH_TOKEN_MAX_AGE_SECONDS"]
        )
    except BadSignature:  # includes SignatureExpired
        return None
    user_id = payload.get("uid") if isinstance(payload, dict) else None
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        return None
    return user_id


def bearer_token(flask_request=None):
    """The token from ``Authorization: Bearer <token>``, or None if absent or malformed."""
    header = (flask_request or request).headers.get("Authorization", "")
    match = _BEARER_PATTERN.match(header.strip())
    if match is None or len(match.group(1)) > MAX_TOKEN_LENGTH:
        return None
    return match.group(1)


# --- guard ----------------------------------------------------------------------------


def set_user_loader(app, loader):
    """Register ``loader(user_id) -> {"user_id", "username", "role"} or None``.

    ``create_app`` registers the database loader from ``app.auth``. ``None`` removes the
    loader, which puts the guard back in its fail-closed state (every protected route 401).
    """
    if loader is None:
        app.extensions.pop(_USER_LOADER_KEY, None)
    else:
        app.extensions[_USER_LOADER_KEY] = loader


def _unauthorized(reason=None):
    challenge = "Bearer" if reason is None else f'Bearer error="{reason}"'
    return AppError(UNAUTHORIZED, headers={"WWW-Authenticate": challenge})


def _authenticate(level):
    token = bearer_token()
    if token is None:
        raise _unauthorized()
    user_id = verify_token(token)
    if user_id is None:
        raise _unauthorized("invalid_token")
    loader = current_app.extensions.get(_USER_LOADER_KEY)
    if loader is None:
        # Fail closed: no way to resolve the account yet (before T2), so nobody gets in.
        logger.warning("a protected route was called but no user loader is registered")
        raise _unauthorized("invalid_token")
    user = loader(user_id)
    if user is None:
        raise _unauthorized("invalid_token")
    # Policy.CUSTOMER.name == "CUSTOMER", matching users.role. AUTHENTICATED accepts any role.
    if level is not Policy.AUTHENTICATED and user.get("role") != level.name:
        raise AppError(FORBIDDEN)
    g.current_user = user


# --- response headers -----------------------------------------------------------------


def init_app(app):
    """Add basic security headers to every API response."""

    @app.after_request
    def add_security_headers(response):
        headers = response.headers
        headers.setdefault("Cache-Control", "no-store")
        headers["X-Content-Type-Options"] = "nosniff"
        headers["Referrer-Policy"] = "no-referrer"
        # The API returns JSON only: nothing in a response may load or be framed.
        headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response
