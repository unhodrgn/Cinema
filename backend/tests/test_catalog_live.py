"""T3: the frontend's real api.js and format.js reading the live catalog (real sockets, Node).

The API and the frontend server run as separate HTTP servers; the catalog is public, so no
login is involved. Needs a disposable PostgreSQL and Node (optional).
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from helpers import fetch
from test_architecture_live import Stack

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js is not installed (optional)")

SCRIPT = """
import {{ createApiClient }} from {api};
import {{ formatDateTime, formatMoney, formatTimeRange }} from {fmt};

const api = createApiClient({{ baseUrl: process.env.API_BASE_URL, storage: {{ getItem: () => null, setItem() {{}}, removeItem() {{}} }} }});
const attempt = async (fn) => {{ try {{ return {{ ok: true, value: await fn() }}; }} catch (e) {{ return {{ ok: false, status: e.status, code: e.code, fields: e.fields }}; }} }};
const day = process.env.DAY;
const movies = await api.get("/api/movies", {{ auth: false }});
const first = movies.movies[0];
const detail = await api.get(`/api/movies/${{first.movie_id}}`, {{ auth: false }});
const all = await api.get("/api/screenings", {{ auth: false, query: {{ date: day }} }});
const one = await api.get("/api/screenings", {{ auth: false, query: {{ date: day, movie_id: first.movie_id }} }});
console.log(JSON.stringify({{
  titles: movies.movies.map((m) => m.title),
  detailMatches: JSON.stringify(detail.movie) === JSON.stringify(first),
  day: all.date,
  count: all.screenings.length,
  perMovie: one.screenings.length,
  times: one.screenings.map((s) => formatTimeRange(s.starts_at, s.ends_at)),
  prices: [...new Set(all.screenings.map((s) => formatMoney(s.ticket_price)))],
  firstStart: formatDateTime(one.screenings[0].starts_at),
  started: all.screenings.some((s) => s.has_started),
  badDate: await attempt(() => api.get("/api/screenings", {{ auth: false, query: {{ date: "2026-13-40" }} }})),
  unknownMovie: await attempt(() => api.get("/api/movies/999999", {{ auth: false }})),
  unknownSchedule: await attempt(() => api.get("/api/screenings", {{ auth: false, query: {{ movie_id: 999999 }} }})),
}}));
"""


def test_the_real_frontend_modules_read_the_live_catalog(fresh_db, tmp_path):
    connection = fresh_db.connect()
    with connection.cursor() as cur:  # tomorrow in the cinema's time zone: always fully in the future
        cur.execute("SELECT ((now() AT TIME ZONE 'Asia/Seoul')::date + 1)::text")
        day = cur.fetchone()[0]
    connection.close()

    script = tmp_path / "catalog_probe.mjs"
    script.write_text(SCRIPT.format(api=json.dumps((FRONTEND_DIR / "js" / "api.js").as_uri()),
                                    fmt=json.dumps((FRONTEND_DIR / "js" / "format.js").as_uri())), encoding="utf-8")
    with Stack(fresh_db.app_config()) as live:
        result = subprocess.run([NODE, str(script)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=120, env={**os.environ, "API_BASE_URL": live.api_origin, "DAY": day})
        assert result.returncode == 0, result.stderr[-2000:]
        out = json.loads(result.stdout.strip().splitlines()[-1])

        # the pages that show it are served by the separate frontend server
        for page in ("/movies.html", "/movie.html", "/screenings.html", "/assets/cinema.js", "/assets/cinema.css"):
            status, headers, _ = fetch(live.frontend_origin + page)
            assert status == 200, page
            assert "connect-src 'self' " + live.api_origin in headers["content-security-policy"]

    assert out["titles"] == ["Jujutsu Kaisen 0", "Jujutsu Kaisen: Hidden Inventory / Premature Death", "Jujutsu Kaisen: Execution", "20th Century Girl", "Exhuma", "Godzilla x Kong: The New Empire"] and out["detailMatches"] is True
    assert out["day"] == day and out["count"] == 20 and out["perMovie"] == 3
    assert out["started"] is False  # tomorrow cannot have started
    assert out["prices"] == ["₩12,000"]
    assert out["firstStart"].startswith(day) and all(re.fullmatch(r"\d\d:\d\d - \d\d:\d\d", t) for t in out["times"])
    assert out["times"] == sorted(out["times"])  # ordered by start time
    assert out["badDate"]["code"] == "validation_error" and "date" in out["badDate"]["fields"]
    assert out["unknownMovie"]["status"] == 404 and out["unknownMovie"]["code"] == "not_found"
    assert out["unknownSchedule"]["status"] == 404
