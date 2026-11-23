"""Cross-origin access for the independent frontend (exact allow-list, no wildcard).

The frontend runs on its own origin (another port, or another machine) and calls this API
with ``fetch``. The browser therefore enforces CORS. This module implements the minimum:

* ``CORS_ALLOWED_ORIGINS`` is a list of exact origins (``scheme://host[:port]``). ``*``,
  paths, queries, fragments and credentials in the URL are rejected at startup.
* A request whose ``Origin`` is in the list gets ``Access-Control-Allow-Origin: <that
  origin>`` on every response, errors included (otherwise the browser would hide the body
  of a 401 or 409 from the page's script). Every other origin gets no CORS header at all.
* ``Vary: Origin`` is added whenever an allow-list exists, so caches never mix the answers.
* A preflight (``OPTIONS`` with ``Access-Control-Request-Method``) is granted only if the
  origin is allowed, the URL matches a real route, the requested method is one of
  ``GET, POST, PUT`` and at least one rule for that URL accepts it, and the requested headers are limited to
  ``Authorization`` and ``Content-Type``. Anything else falls through to Flask's normal
  handling, which carries no permission, so the browser blocks the real request.
* ``Access-Control-Allow-Credentials`` is never sent: authentication is a Bearer token in
  the ``Authorization`` header, not a cookie.

With an empty allow-list (the default) no CORS header is ever added: same-origin only.
"""

from urllib.parse import urlsplit

from flask import current_app, g, request

ALLOWED_METHODS = ("GET", "POST", "PUT")
ALLOWED_HEADERS = ("Authorization", "Content-Type")
PREFLIGHT_MAX_AGE_SECONDS = 600

_DEFAULT_PORTS = {"http": 80, "https": 443}


class OriginError(ValueError):
    """A configured origin is not a plain ``scheme://host[:port]``."""


def normalize_origin(value):
    """The canonical ``scheme://host[:port]`` for ``value``, or raise ``OriginError``.

    Scheme and host are lower-cased and a default port (80 for http, 443 for https) is
    dropped, which is how browsers serialize the ``Origin`` header. A single trailing
    slash is tolerated; any other path, a query, a fragment or user info is not.
    """
    text = (value or "").strip()
    if not text or "*" in text:
        raise OriginError(f"{text!r} is not an exact origin (wildcards are not allowed)")
    try:
        parts = urlsplit(text)
        port = parts.port
    except ValueError:
        raise OriginError(f"{text!r} is not a valid origin") from None
    if parts.scheme not in _DEFAULT_PORTS or not parts.hostname:
        raise OriginError(f"{text!r} must look like http(s)://host[:port]")
    if parts.path not in ("", "/") or parts.query or parts.fragment or parts.username is not None:
        raise OriginError(f"{text!r} must contain only scheme, host and optional port")
    host = parts.hostname
    if ":" in host:  # IPv6 literal
        host = f"[{host}]"
    origin = f"{parts.scheme}://{host}"
    if port is not None and port != _DEFAULT_PORTS[parts.scheme]:
        origin += f":{port}"
    return origin


def parse_origin_list(value):
    """A tuple of canonical origins from a comma-separated string or an iterable.

    Blank entries are ignored and duplicates removed (order kept). Raises ``OriginError``
    for the first invalid entry.
    """
    if value is None:
        return ()
    items = value.split(",") if isinstance(value, str) else list(value)
    origins = []
    for item in items:
        if isinstance(item, str) and not item.strip():
            continue
        origin = normalize_origin(item)
        if origin not in origins:
            origins.append(origin)
    return tuple(origins)


def _request_origin(allowed):
    """The request's ``Origin`` if it is in ``allowed``, else None."""
    header = request.headers.get("Origin")
    if not header:
        return None
    try:
        origin = normalize_origin(header)
    except OriginError:
        return None  # includes "null"
    return origin if origin in allowed else None


def _preflight_is_acceptable():
    method = (request.headers.get("Access-Control-Request-Method") or "").strip().upper()
    if method not in ALLOWED_METHODS:
        return False
    # Every rule that matches the path counts: a URL served by separate GET and POST rules
    # (``@bp.get`` + ``@bp.post``) must accept a preflight for either method. ``request.url_rule``
    # is only the FIRST matching rule, so it is not enough. Unknown paths give an empty list.
    if method not in current_app.create_url_adapter(request).allowed_methods():
        return False
    requested = request.headers.get("Access-Control-Request-Headers", "")
    allowed = {name.lower() for name in ALLOWED_HEADERS}
    return all(
        name.strip().lower() in allowed for name in requested.split(",") if name.strip()
    )


def init_app(app):
    """Read ``CORS_ALLOWED_ORIGINS`` (validated again, so test overrides are safe) and hook in."""
    allowed = frozenset(parse_origin_list(app.config.get("CORS_ALLOWED_ORIGINS")))
    app.config["CORS_ALLOWED_ORIGINS"] = tuple(sorted(allowed))
    if not allowed:
        return

    def is_preflight():
        return request.method == "OPTIONS" and "Access-Control-Request-Method" in request.headers

    @app.before_request
    def answer_preflight():
        if not is_preflight():
            return None
        if _request_origin(allowed) is None or not _preflight_is_acceptable():
            return None  # no permission is granted; Flask answers as usual
        g.cors_preflight_granted = True
        response = app.make_response(("", 204))
        response.headers["Access-Control-Allow-Methods"] = ", ".join(ALLOWED_METHODS)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(ALLOWED_HEADERS)
        response.headers["Access-Control-Max-Age"] = str(PREFLIGHT_MAX_AGE_SECONDS)
        return response

    @app.after_request
    def add_cors_headers(response):
        response.vary.add("Origin")
        origin = _request_origin(allowed)
        # A preflight that was not granted carries no CORS header at all, even when the
        # origin itself is allowed (unknown path, a method or header the API does not use).
        if origin is not None and (not is_preflight() or g.get("cors_preflight_granted")):
            response.headers["Access-Control-Allow-Origin"] = origin
        return response
