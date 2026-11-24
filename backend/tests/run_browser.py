"""Run Playwright against an owned, newly seeded database and two local HTTP servers."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from threading import Thread

from dotenv import dotenv_values
from werkzeug.serving import make_server

from disposable_db import CURRENT_SCHEMA_PATHS, SEED_PATH, provision_database, read_forbidden_names, read_server_settings
from helpers import free_port, load_frontend_server

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app import create_app


def main():
    dotenv = dotenv_values(os.environ.get("CINEMA_TEST_ENV_FILE", ROOT / ".env"))
    settings = read_server_settings(os.environ, dotenv)
    front = load_frontend_server()
    with provision_database(settings, CURRENT_SCHEMA_PATHS, SEED_PATH, read_forbidden_names(os.environ, dotenv)) as db:
        api_port = free_port()
        static = front.create_server(front.Settings("127.0.0.1", 0, f"http://127.0.0.1:{api_port}"))
        origin = f"http://127.0.0.1:{static.server_port}"
        try:
            app = create_app("testing", dict(db.app_config(), CORS_ALLOWED_ORIGINS=origin))
            api = make_server("127.0.0.1", api_port, app, threaded=True)
        except BaseException:
            static.server_close()
            raise
        servers = [api, static]
        threads = [Thread(target=server.serve_forever, daemon=True) for server in servers]
        for thread in threads:
            thread.start()
        try:
            with tempfile.TemporaryDirectory() as output:
                cli = ROOT / "frontend/node_modules/@playwright/test/cli.js"
                env = dict(os.environ, CINEMA_E2E_ORIGIN=origin, CINEMA_E2E_OUTPUT=output)
                return subprocess.run([shutil.which("node") or "node", str(cli), "test"],
                                      cwd=ROOT / "frontend", env=env).returncode
        finally:
            for server in servers:
                server.shutdown()
                server.server_close()
            for thread in threads:
                thread.join()


if __name__ == "__main__":
    raise SystemExit(main())
