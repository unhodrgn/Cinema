"""T1: run the frontend's own JavaScript tests with Node's built-in test runner.

Node is an optional development prerequisite (no npm packages are used). Without it these
tests are skipped; the frontend is still covered by the static rules in
test_frontend_static.py and by the Python tests of the server.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js is not installed (optional)")


def node_test(*files):
    return subprocess.run(
        [NODE, "--test", *files],
        cwd=FRONTEND,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def test_frontend_unit_tests_pass():
    # Every test file is run: a list kept by hand forgot seats.test.js once.
    files = sorted(path.relative_to(FRONTEND).as_posix() for path in (FRONTEND / "tests").glob("*.test.js"))
    assert {"tests/admin.test.js", "tests/seats.test.js"} <= set(files)
    result = node_test(*files)

    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-1000:]
    counts = dict(re.findall(r"^ℹ (tests|pass|fail) (\d+)", result.stdout, flags=re.MULTILINE))
    assert counts.get("fail") == "0"
    assert int(counts["tests"]) >= 20
    assert counts["pass"] == counts["tests"]
