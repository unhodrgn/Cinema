"""Full verification entry point used by Compose and local development."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

from dotenv import dotenv_values
from disposable_db import check_server, read_server_settings

ROOT = Path(__file__).resolve().parents[2]


def main():
    settings = read_server_settings(os.environ, dotenv_values(os.environ.get("CINEMA_TEST_ENV_FILE", ROOT / ".env")))
    check_server(settings)
    for name in ("node", "npm", "psql"):
        if not shutil.which(name):
            raise SystemExit(f"Full verification requires {name}")
    # pytest also invokes node --test. Live tests using Node run separately inside pytest.
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    for target in ("build", "build:legacy"):
        subprocess.run([npm, "run", target], cwd=ROOT / "frontend", check=True)
    result = subprocess.run([sys.executable, "-m", "pytest", "-ra", "backend/tests"], cwd=ROOT,
                            env=dict(os.environ, CINEMA_REQUIRE_LIVE_DB="1"))
    if result.returncode:
        return result.returncode
    subprocess.run([sys.executable, str(ROOT / "backend/tests/run_database.py")], check=True)
    return subprocess.run([sys.executable, str(ROOT / "backend/tests/run_browser.py")]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
