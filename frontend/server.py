"""Static file server for the independent frontend (Python standard library only).

This process serves the files in this directory and nothing else. It has no database, no
Flask and no access to the backend's code: the pages it serves talk to the REST API over
HTTP from the user's browser. It can be started, stopped and moved to another machine
independently of the API and of PostgreSQL.

Configuration (environment variables only, nothing is read from files):

    FRONTEND_HOST   address to listen on        default 127.0.0.1  (0.0.0.0 = all interfaces)
    FRONTEND_PORT   port to listen on           default 8080
    API_BASE_URL    origin of the REST API      default http://localhost:5000
                    (what the *browser* must use: an address reachable from the device that
                    shows the page, e.g. http://192.168.0.10:5000 for a second device)

``/config.js`` is generated from ``API_BASE_URL`` on every request; there is no such file.

Run:  python frontend/server.py

Security notes
    * Only GET and HEAD. Every other method is answered 405.
    * Only files below this directory, only with an allow-listed extension, never dot-files
      or the ``tests`` / ``node_modules`` directories. ``..``, backslashes, NUL, drive
      letters / alternate data streams (``:``) and symbolic links that leave the directory
      are refused (404). No directory listings.
    * Every response carries a Content-Security-Policy that allows scripts and styles only
      from this server and network connections only to this server and ``API_BASE_URL``,
      plus nosniff, no-referrer and frame-denial headers.
    * Error pages are plain text and never echo the request.
"""

import json
import os
import socketserver
import sys
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_API_BASE_URL = "http://localhost:5000"

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".ico": "image/x-icon",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".woff2": "font/woff2",
}
HIDDEN_DIRECTORIES = {"tests", "node_modules", "__pycache__"}
CONFIG_PATH = "config.js"
INDEX_FILE = "index.html"
MAX_SEGMENT_LENGTH = 255

# On Windows SO_REUSEADDR lets a second process bind a port that is already in use, which
# would hide "address already in use" and allow port hijacking. Keep it off there.
socketserver.TCPServer.allow_reuse_address = os.name != "nt"


class SettingsError(ValueError):
    """An environment variable is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    api_base_url: str


def normalize_origin(value):
    """``scheme://host[:port]`` for an http(s) origin, or raise ``SettingsError``.

    (A small copy of the backend's rule on purpose: the frontend never imports backend code.)
    """
    text = (value or "").strip()
    if not text or "*" in text:
        raise SettingsError(f"{text!r} is not an exact origin")
    try:
        parts = urlsplit(text)
        port = parts.port
    except ValueError:
        raise SettingsError(f"{text!r} is not a valid origin") from None
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise SettingsError(f"{text!r} must look like http(s)://host[:port]")
    if parts.path not in ("", "/") or parts.query or parts.fragment or parts.username is not None:
        raise SettingsError(f"{text!r} must contain only scheme, host and optional port")
    host = f"[{parts.hostname}]" if ":" in parts.hostname else parts.hostname
    origin = f"{parts.scheme}://{host}"
    if port is not None and port != {"http": 80, "https": 443}[parts.scheme]:
        origin += f":{port}"
    return origin


def read_settings(environ=None):
    """Settings from the environment (blank values count as unset)."""
    environ = os.environ if environ is None else environ

    def value(name, default):
        text = (environ.get(name) or "").strip()
        return text or default

    host = value("FRONTEND_HOST", DEFAULT_HOST)
    if any(character.isspace() for character in host) or "/" in host:
        raise SettingsError("FRONTEND_HOST must be a host name or IP address")
    port_text = value("FRONTEND_PORT", str(DEFAULT_PORT))
    try:
        port = int(port_text)
    except ValueError:
        raise SettingsError("FRONTEND_PORT must be an integer") from None
    if not 1 <= port <= 65535:
        raise SettingsError("FRONTEND_PORT must be between 1 and 65535")
    api_base_url = normalize_origin(value("API_BASE_URL", DEFAULT_API_BASE_URL))
    return Settings(host=host, port=port, api_base_url=api_base_url)


# --- request path handling ------------------------------------------------------------


def _is_inside(root, path):
    root_key, path_key = os.path.normcase(str(root)), os.path.normcase(str(path))
    try:
        return os.path.commonpath([root_key, path_key]) == root_key
    except ValueError:  # different drives
        return False


def resolve_request_path(root, target):
    """The file to serve for a request target, or None (-> 404).

    ``target`` is the raw request target. The query and fragment are dropped, the path is
    percent-decoded exactly once and then validated segment by segment.
    """
    root = Path(os.path.realpath(root))
    raw = target.split("?", 1)[0].split("#", 1)[0]
    path = unquote(raw)
    if "\x00" in path or "\\" in path or not path.startswith("/"):
        return None
    segments = []
    for segment in path.split("/"):
        if segment in ("", "."):
            continue
        if (
            segment == ".."
            or segment.startswith(".")
            or ":" in segment
            or len(segment) > MAX_SEGMENT_LENGTH
            or segment.lower() in HIDDEN_DIRECTORIES
            or any(ord(character) < 32 for character in segment)
        ):
            return None
        segments.append(segment)
    candidate = root.joinpath(*segments) if segments else root
    if candidate.is_dir():
        candidate = candidate / INDEX_FILE
    try:
        real = Path(os.path.realpath(candidate))
    except (OSError, ValueError):
        return None
    if not _is_inside(root, real) or not real.is_file():
        return None
    # The extension of the requested name AND of the resolved file must be allowed, so a
    # link or a Windows trailing-dot name cannot reach server.py, package.json or the like.
    if candidate.suffix.lower() not in CONTENT_TYPES or real.suffix.lower() not in CONTENT_TYPES:
        return None
    try:
        parts = real.relative_to(root).parts
    except ValueError:
        return None
    if any(part.lower() in HIDDEN_DIRECTORIES or part.startswith(".") for part in parts):
        return None
    return real


# --- the server -----------------------------------------------------------------------


def content_security_policy(api_base_url):
    return "; ".join(
        [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self'",
            "img-src 'self' data:",
            "font-src 'self'",
            f"connect-src 'self' {api_base_url}",
            "object-src 'none'",
            "base-uri 'none'",
            "form-action 'none'",
            "frame-ancestors 'none'",
        ]
    )


def config_script(api_base_url):
    """The body of ``/config.js``: the only deployment setting the browser needs."""
    return f"window.APP_CONFIG = Object.freeze({json.dumps({'apiBaseUrl': api_base_url})});\n"


class FrontendHandler(BaseHTTPRequestHandler):
    server_version = "CinemaFrontend"
    sys_version = ""  # do not announce the Python version

    def version_string(self):
        return self.server_version  # the default adds a trailing space when sys_version is empty

    # -- helpers --

    def _security_headers(self):
        self.send_header("Content-Security-Policy", self.server.csp)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Permissions-Policy", "geolocation=(), camera=(), microphone=()")

    def _respond(self, status, body, content_type, cache="no-cache", send_body=True, extra=()):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        for name, value in extra:
            self.send_header(name, value)
        self._security_headers()
        self.end_headers()
        if send_body:
            self.wfile.write(body)

    def send_error(self, code, message=None, explain=None):
        """Plain-text error pages that never echo the request."""
        try:
            phrase = HTTPStatus(code).phrase
        except ValueError:
            phrase = "Error"
        body = f"{code} {phrase}\n".encode("ascii")
        extra = [("Allow", "GET, HEAD")] if code == 405 else []
        self._respond(code, body, "text/plain; charset=utf-8", cache="no-store",
                      send_body=self.command != "HEAD", extra=extra)

    # -- methods --

    def _serve(self, send_body):
        if self.path.split("?", 1)[0].split("#", 1)[0] == "/" + CONFIG_PATH:
            body = config_script(self.server.settings.api_base_url).encode("utf-8")
            self._respond(200, body, CONTENT_TYPES[".js"], cache="no-store", send_body=send_body)
            return
        file = resolve_request_path(self.server.root, self.path)
        if file is None:
            self.send_error(404)
            return
        try:
            body = file.read_bytes()
        except OSError:
            self.send_error(404)
            return
        self._respond(200, body, CONTENT_TYPES[file.suffix.lower()], send_body=send_body)

    def do_GET(self):
        self._serve(send_body=True)

    def do_HEAD(self):
        self._serve(send_body=False)

    def _method_not_allowed(self):
        self.send_error(405)

    do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_TRACE = do_CONNECT = _method_not_allowed


class FrontendServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, settings, root):
        super().__init__(address, FrontendHandler)
        self.settings = settings
        self.root = Path(root)
        self.csp = content_security_policy(settings.api_base_url)


def create_server(settings, root=ROOT):
    """A ready (bound, not yet serving) server. ``settings.port`` 0 picks a free port."""
    return FrontendServer((settings.host, settings.port), settings, root)


def main():
    try:
        settings = read_settings()
    except SettingsError as error:
        print(f"frontend server: invalid configuration: {error}", file=sys.stderr)
        return 2
    try:
        server = create_server(settings)
    except OSError as error:
        print(f"frontend server: cannot listen on {settings.host}:{settings.port}: {error.strerror}",
              file=sys.stderr)
        return 1
    shown = settings.host if settings.host not in ("0.0.0.0", "::") else "<this machine's address>"
    print(f"Frontend server: http://{shown}:{server.server_port}  (serving {server.root})")
    print(f"API the pages will call: {settings.api_base_url}")
    if settings.host in ("0.0.0.0", "::"):
        print("Listening on ALL interfaces: reachable from other devices on the network.")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
