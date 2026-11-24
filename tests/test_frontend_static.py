"""T1: architecture rules for the independent frontend, checked statically.

The frontend must have no database access, no backend imports, no template syntax, no
unsafe DOM sinks and no third-party resources; the backend must render nothing.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
APP = ROOT / "app"

# Files that ship to the browser (the node tests and server.py are checked separately).
BROWSER_FILES = sorted(
    path
    for path in FRONTEND.rglob("*")
    if path.is_file()
    and path.suffix in {".html", ".js", ".css"}
    and "tests" not in path.relative_to(FRONTEND).parts
    and "node_modules" not in path.relative_to(FRONTEND).parts
)
ALL_FRONTEND_TEXT_FILES = sorted(
    path
    for path in FRONTEND.rglob("*")
    if path.is_file()
    and path.suffix in {".html", ".js", ".css", ".py", ".json", ".md", ".txt"}
    and "node_modules" not in path.relative_to(FRONTEND).parts
)


def strip_js_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"(^|[\s;{}()])//[^\n]*", r"\1", text)


def strip_css_comments(text):
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def python_code(text):
    """Python source without docstrings and comment lines (prose may mention PostgreSQL)."""
    import ast

    lines = text.splitlines()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            first = node.body[0] if node.body else None
            is_docstring = (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            )
            if is_docstring:
                for number in range(first.lineno - 1, first.end_lineno):
                    lines[number] = ""
    return "\n".join(line for line in lines if not line.lstrip().startswith("#"))


def code_of(path):
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".py":
        return python_code(text)
    if path.suffix == ".js":
        return strip_js_comments(text)
    if path.suffix == ".css":
        return strip_css_comments(text)
    if path.suffix == ".html":
        return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return text


def test_the_frontend_has_files_to_check():
    names = {path.name for path in BROWSER_FILES}

    assert {"index.html", "style.css", "api.js", "ui.js", "index.js"} <= names


# --- no database, no backend --------------------------------------------------------------

DATABASE_MARKERS = [
    r"psycopg", r"postgres", r"sqlalchemy", r"\bDB_(HOST|PORT|NAME|USER|PASSWORD)\b",
    r"\bSECRET_KEY\b", r"password_hash", r"\bpg_",
    r"\bSELECT\b[^;\n]*\bFROM\b", r"\bINSERT\s+INTO\b", r"\bDELETE\s+FROM\b",
    r"\bUPDATE\b[^;\n]*\bSET\b", r"\bCREATE\s+(TABLE|FUNCTION|TRIGGER)\b",
    r"\bcreate_booking\b", r"\bpay_booking\b", r"\bcancel_booking\b", r"\bexpire_overdue_bookings\b",
]


@pytest.mark.parametrize("path", ALL_FRONTEND_TEXT_FILES, ids=lambda p: str(p.relative_to(FRONTEND)))
def test_no_database_access_credentials_or_sql_in_the_frontend(path):
    # Code only: prose in comments and docstrings may legitimately name PostgreSQL.
    code = code_of(path) if path.suffix in {".html", ".js", ".css", ".py"} else path.read_text(encoding="utf-8")

    for marker in DATABASE_MARKERS:
        assert not re.search(marker, code, flags=re.IGNORECASE), f"{path.name} matches {marker!r}"


def js_import_specifiers(text):
    pattern = r"""(?:import\s+(?:[^'"]*?\s+from\s+)?|import\(\s*)['"]([^'"]+)['"]"""
    return re.findall(pattern, strip_js_comments(text))


@pytest.mark.parametrize(
    "path", [p for p in FRONTEND.rglob("*.js") if "node_modules" not in p.parts], ids=lambda p: str(p.relative_to(FRONTEND))
)
def test_javascript_imports_stay_inside_the_frontend(path):
    for specifier in js_import_specifiers(path.read_text(encoding="utf-8")):
        if specifier.startswith("node:"):
            assert "tests" in path.relative_to(FRONTEND).parts, f"{path.name} imports {specifier}"
            continue
        assert specifier.startswith(("./", "../")), f"{path.name}: bare import {specifier}"
        target = (path.parent / specifier).resolve()
        assert target.is_relative_to(FRONTEND.resolve()), f"{path.name} imports outside frontend: {specifier}"
        assert target.exists(), f"{path.name} imports a missing file: {specifier}"
        assert "app" not in target.relative_to(FRONTEND.resolve()).parts[:1]


def test_the_frontend_never_references_backend_source_paths():
    for path in ALL_FRONTEND_TEXT_FILES:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"(\.\./)+app/|/app/(config|database|errors|__init__)", text), path.name


def test_package_json_declares_no_dependencies():
    package = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))

    assert package["private"] is True
    assert package["type"] == "module"
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        assert key not in package


def test_there_is_no_committed_config_file_and_no_credentials_file():
    assert not (FRONTEND / "config.js").exists()
    for name in (".env", ".env.local", "credentials.json", "secrets.json"):
        assert not (FRONTEND / name).exists()


# --- no template syntax, no unsafe DOM sinks, no third-party resources --------------------

UNSAFE_SINKS = [
    r"\.innerHTML\b", r"\.outerHTML\b", r"insertAdjacentHTML", r"document\.write", r"\beval\s*\(",
    r"new\s+Function\b", r"setTimeout\s*\(\s*['\"`]", r"setInterval\s*\(\s*['\"`]",
    r"\.srcdoc\b", r"createContextualFragment", r"DOMParser", r"javascript:",
]


@pytest.mark.parametrize("path", BROWSER_FILES, ids=lambda p: str(p.relative_to(FRONTEND)))
def test_no_unsafe_dom_sinks(path):
    code = code_of(path)

    for sink in UNSAFE_SINKS:
        assert not re.search(sink, code, flags=re.IGNORECASE), f"{path.name} uses {sink}"


@pytest.mark.parametrize("path", [p for p in BROWSER_FILES if p.suffix == ".html"], ids=lambda p: p.name)
def test_html_pages_are_static_and_csp_friendly(path):
    code = code_of(path)

    assert "{{" not in code and "{%" not in code and "{#" not in code, "template syntax"
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", code, flags=re.IGNORECASE), "inline script"
    assert not re.search(r"\son[a-z]+\s*=", code, flags=re.IGNORECASE), "inline event handler"
    assert not re.search(r"\sstyle\s*=", code, flags=re.IGNORECASE), "inline style attribute"
    assert not re.search(r"<style\b", code, flags=re.IGNORECASE), "inline style element"
    assert not re.search(r"<(iframe|object|embed|base)\b", code, flags=re.IGNORECASE)
    assert "<!doctype html>" in code.lower()
    assert re.search(r"<html[^>]*\blang=", code, flags=re.IGNORECASE)
    assert re.search(r'<meta name="viewport"', code)


@pytest.mark.parametrize("path", BROWSER_FILES, ids=lambda p: str(p.relative_to(FRONTEND)))
def test_no_third_party_or_absolute_urls_in_browser_files(path):
    code = code_of(path)

    assert not re.search(r"https?://", code, flags=re.IGNORECASE), "external URL"
    assert not re.search(r"@import\s+url", code, flags=re.IGNORECASE)
    assert "cdn." not in code.lower()


def test_html_resources_are_local_files_that_exist():
    for page in (p for p in BROWSER_FILES if p.suffix == ".html"):
        for target in re.findall(r"""(?:src|href)=["']([^"']+)["']""", code_of(page)):
            if target.startswith(("#", "?")) or target == "/":
                continue  # "/" is the index page
            assert target.startswith("/"), f"{page.name}: {target} must be a root-relative path"
            if target == "/config.js":
                continue  # generated by the frontend server
            assert (FRONTEND / target.lstrip("/")).is_file(), f"{page.name}: missing {target}"


def test_every_page_loads_config_before_its_module():
    for page in (p for p in BROWSER_FILES if p.suffix == ".html"):
        code = code_of(page)
        if 'type="module"' in code:
            assert code.index('src="/config.js"') < code.index('type="module"'), page.name


# --- the backend renders nothing ----------------------------------------------------------

RENDERING = [
    r"render_template", r"render_template_string", r"send_from_directory", r"send_file",
    r"jinja2", r"Markup", r"\|\s*safe\b", r"make_response\([^)]*<",
]


def test_backend_code_renders_no_pages_and_serves_no_files():
    for path in sorted(APP.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        for pattern in RENDERING:
            assert not re.search(pattern, code), f"{path.name} matches {pattern!r}"


def test_the_backend_disables_static_files_and_templates_explicitly():
    source = (APP / "__init__.py").read_text(encoding="utf-8")

    assert "static_folder=None" in source and "template_folder=None" in source


# --- regression (Phase 5 browser check, #12): no developer-facing text on the home page ------------

DEVELOPER_TEXT = ["frontend server", "database access", "api address", "rest api", "over http", "api_base_url",
                  "reported by the api"]


def test_the_home_page_has_no_developer_facing_text():
    html = code_of(FRONTEND / "index.html").lower()  # comments are not shown to anyone
    script = code_of(FRONTEND / "js" / "pages" / "index.js").lower()

    for phrase in DEVELOPER_TEXT:
        assert phrase not in html, phrase
    assert "api-address" not in html and "api-address" not in script


# --- regression (Phase 5 browser check, #6 and #7) -------------------------------------------------


def test_pages_ask_who_is_logged_in_only_through_pageUser_so_a_network_error_never_means_logged_out():
    """#6: `auth.currentUser()` throws for an unreachable API. Pages that turned the throw into
    "no user" redirected to the login page. Only nav (shows links), login (form explains) and
    auth.js itself (pageUser) may call it directly."""
    allowed = {"nav.js", "login.js", "auth.js"}
    offenders = [
        path.name
        for path in (FRONTEND / "js").rglob("*.js")
        if path.name not in allowed and re.search(r"\.currentUser\(", code_of(path))
    ]

    assert offenders == []
    for name in ("booking.js", "bookings.js", "seats.js"):
        assert "pageUser(" in code_of(FRONTEND / "js" / "pages" / name), name
    assert "pageUser(" in code_of(FRONTEND / "js" / "admin.js")


def test_booking_pages_show_the_screening_date_not_only_the_time():
    """#7: a booking is for a day, not just for a clock time."""
    for name in ("booking.js", "bookings.js"):
        code = code_of(FRONTEND / "js" / "pages" / name)
        assert "formatDateTimeRange(" in code, name
        assert "formatTimeRange(" not in code, name


def test_the_booking_page_asks_the_server_again_when_the_countdown_ends():
    """#3: reaching zero must not leave a stale BOOKED / Pay Now on screen."""
    code = code_of(FRONTEND / "js" / "pages" / "booking.js")

    assert "createCountdown(" in code and "confirmExpiry(" in code
    assert "payButton.disabled = true" in code


def _css_block(css, selector):
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert match, selector
    return match.group(1)


def test_the_seat_grid_can_shrink_to_fit_a_375px_phone():
    """#5: ten fixed 2.2rem seats plus gaps made a 432px grid that overflowed a 375px card.
    Layout cannot be measured here, so this guards the rules that make it shrink (the real
    check is done in a browser)."""
    css = code_of(FRONTEND / "css" / "style.css")
    grid, row, button = _css_block(css, ".seat-grid"), _css_block(css, ".seat-row"), _css_block(css, ".seat-btn")

    assert "max-width: 100%" in grid
    assert "display: grid" in row and row.count("repeat(5, minmax(0,") == 2  # seats 1-5 | aisle | seats 6-10
    assert "width: 100%" in button and "aspect-ratio: 1" in button and "min-width: 0" in button
    assert not re.search(r"(^|\n)\s*width:\s*2\.2rem", button)  # no fixed seat width

    # The narrow-screen override has the same specificity as the base rule, so it must come after.
    narrow = css.index("  .seat-row { gap: 2px;")
    assert narrow > css.index(".seat-row {") and narrow > css.index(".seat-btn {")


TMDB_NOTICE = "Movie posters: TMDB. This product uses the TMDB API but is not endorsed or certified by TMDB."
PAGES = sorted(FRONTEND.glob("*.html"))


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_every_page_has_the_tmdb_attribution_in_its_footer(page):
    html = page.read_text(encoding="utf-8")

    assert f'<footer class="site-footer">{TMDB_NOTICE}</footer>' in html
    assert html.count("<footer") == 1 and html.index("</main>") < html.index("<footer")


def test_there_are_twelve_pages_and_all_are_checked_for_the_footer():
    assert len(PAGES) == 12 and {"admin-movies.html", "admin-screenings.html", "admin-bookings.html"} <= {p.name for p in PAGES}


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_every_page_declares_the_dark_color_scheme(page):
    assert '<meta name="color-scheme" content="dark">' in page.read_text(encoding="utf-8")


def test_the_stylesheet_is_dark_only_with_self_hosted_fonts():
    css = code_of(FRONTEND / "css" / "style.css")

    assert "color-scheme: dark" in css and "prefers-color-scheme" not in css
    for token in ("#0e0e10", "#141416", "#2a2a2f", "#f2f0eb", "#b9b5b0", "#d7263d"):
        assert token in css.lower(), token
    assert not re.search(r"https?:|//fonts\.|@import", css)  # nothing from another host
    urls = re.findall(r'url\("\.\./(fonts/[^"]+)"\)', css)
    assert len(urls) == 4
    for url in urls:
        assert (FRONTEND / url).is_file(), url
    assert (FRONTEND / "fonts" / "LICENSE-inter.txt").is_file() and (FRONTEND / "fonts" / "LICENSE-bebas-neue.txt").is_file()


def test_posters_are_shown_in_a_fixed_2_3_frame_that_covers():
    css = code_of(FRONTEND / "css" / "style.css")
    frame, image = _css_block(css, ".poster"), _css_block(css, ".poster-img")

    assert "aspect-ratio: 2 / 3" in frame and "overflow: hidden" in frame
    assert "object-fit: cover" in image and "width: 100%" in image and "height: 100%" in image


def test_the_admin_screenings_page_locks_edit_through_screeningEditLock():
    """B: started screenings (and screenings with bookings) get a disabled Edit button."""
    code = code_of(FRONTEND / "js" / "pages" / "admin_screenings.js")

    assert "screeningEditLock(" in code and "disabled: lock.disabled" in code and "title: lock.title" in code
    assert "has_bookings ?" not in code  # the old inline D2-only check is gone
