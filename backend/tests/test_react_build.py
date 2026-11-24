"""Check the active frontend source and built pages in addition to the rollback bundle."""
import re
from pathlib import Path

import pytest

from test_frontend_static import DATABASE_MARKERS, UNSAFE_SINKS, strip_js_comments

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
PAGES = {path.name for path in (FRONTEND / "legacy").glob("*.html")}
SOURCES = sorted(path for path in (FRONTEND / "src").rglob("*") if path.suffix in {".ts", ".tsx"})


@pytest.mark.parametrize("path", SOURCES, ids=lambda path: path.relative_to(FRONTEND).as_posix())
def test_browser_modules_keep_the_api_boundary_and_render_data_as_text(path):
    source = strip_js_comments(path.read_text(encoding="utf8"))
    for marker in DATABASE_MARKERS + UNSAFE_SINKS + ["dangerouslySetInnerHTML"]:
        assert not re.search(marker, source, re.I), marker
    for specifier in re.findall(r'''from\s+["']([^"']+)["']''', source):
        if specifier in {"react", "react-dom/client"}:
            continue
        assert specifier.startswith(".")
        target = (path.parent / specifier).resolve()
        assert target.is_relative_to(FRONTEND)
        assert any(candidate.is_file() for candidate in (target, target.with_suffix(".tsx"), target.with_suffix(".ts")))


def test_the_build_preserves_every_page_url_and_loads_runtime_config_first():
    public = FRONTEND / "dist"
    assert len(PAGES) == 12
    assert {page.name for page in public.glob("*.html")} == PAGES
    for page in PAGES:
        html = (public / page).read_text(encoding="utf8")
        assert html.index('src="/config.js"') < html.index('type="module"')
        for asset in re.findall(r'''(?:src|href)="(/assets/[^"]+)"''', html):
            assert (public / asset[1:]).is_file()
    assert not (public / "config.js").exists()
    assert not (public / ".env").exists()
