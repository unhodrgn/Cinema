"""T1: the frontend server and the API as two REAL operating-system processes.

Started exactly as a person would start them (``python frontend/server.py`` and
``flask --app app run``), each with its own environment, stopped and restarted
independently. The API process is pointed at a closed database port (``DB_PORT=1``), so no
PostgreSQL server is contacted and no real database is touched: this also shows that the
API stays alive and answers safely when its database is unreachable.
"""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from helpers import fetch, free_port, is_refused, wait_until_refused, wait_until_serving

ROOT = Path(__file__).resolve().parents[1]
STARTUP_SECONDS = 30

# Everything the application reads: removed from the child environment so that nothing
# from the developer's real configuration can leak into (or be reached by) these processes.
SCRUBBED = ("SECRET_KEY", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD",
            "DB_CONNECT_TIMEOUT", "APP_TIMEZONE", "FLASK_DEBUG", "CORS_ALLOWED_ORIGINS",
            "AUTH_TOKEN_MAX_AGE_SECONDS", "FRONTEND_HOST", "FRONTEND_PORT", "API_BASE_URL",
            "PGHOST", "PGPORT", "PGUSER", "PGPASSWORD", "PGDATABASE", "FLASK_APP", "FLASK_RUN_PORT",
            "FLASK_RUN_HOST", "TEST_DB_PORT", "TEST_DB_HOST", "TEST_DB_ADMIN_USER", "TEST_DB_ADMIN_PASSWORD")


def clean_environment(**extra):
    env = {key: value for key, value in os.environ.items() if key.upper() not in SCRUBBED}
    env.update({"PYTHONUNBUFFERED": "1", "FLASK_SKIP_DOTENV": "1"})
    env.update(extra)
    return env


class Process:
    def __init__(self, args, env, log_path):
        self.log_path = log_path
        self._log = open(log_path, "wb")
        self.popen = subprocess.Popen(args, cwd=ROOT, env=env, stdout=self._log, stderr=subprocess.STDOUT)

    @property
    def pid(self):
        return self.popen.pid

    def running(self):
        return self.popen.poll() is None

    def stop(self):
        """Stop the process AND its children.

        On Windows a virtual environment's ``python.exe`` is a launcher that starts the real
        interpreter as a child, so terminating only the launcher is not enough.
        """
        if self.running():
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(self.popen.pid), "/T", "/F"],
                               capture_output=True, timeout=30)
            else:
                self.popen.terminate()
            try:
                self.popen.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover
                self.popen.kill()
                self.popen.wait(timeout=10)
        self._log.close()

    def output(self):
        self._log.flush()
        return Path(self.log_path).read_text(encoding="utf-8", errors="replace")


class Deployment:
    """Frontend server + API as two processes (Tier 1: one machine, two ports)."""

    def __init__(self, tmp_path, cors=True):
        self.tmp_path = tmp_path
        self.frontend_port = free_port()
        self.api_port = free_port()
        self.frontend_origin = f"http://127.0.0.1:{self.frontend_port}"
        self.api_origin = f"http://127.0.0.1:{self.api_port}"
        self.cors = self.frontend_origin if cors else ""
        self.frontend = None
        self.api = None
        self.starts = 0

    def start_frontend(self):
        env = clean_environment(FRONTEND_HOST="127.0.0.1", FRONTEND_PORT=str(self.frontend_port),
                                API_BASE_URL=self.api_origin)
        self.frontend = Process([sys.executable, str(ROOT.parent / "frontend" / "server.py")], env,
                                self.tmp_path / "frontend.log")
        wait_until_serving(self.frontend_origin + "/index.html", STARTUP_SECONDS)

    def start_api(self, wait=True):
        self.starts += 1
        env = clean_environment(
            SECRET_KEY="process-test-secret-key-not-a-real-one",
            DB_HOST="127.0.0.1", DB_PORT="1", DB_NAME="cinema_process_probe", DB_USER="probe",
            DB_CONNECT_TIMEOUT="1", CORS_ALLOWED_ORIGINS=self.cors,
        )
        self.api = Process(
            [sys.executable, "-m", "flask", "--app", "app", "run", "--host", "127.0.0.1",
             "--port", str(self.api_port), "--no-reload", "--no-debugger"],
            env, self.tmp_path / f"api{self.starts}.log",
        )
        if wait:
            wait_until_serving(self.api_origin + "/health", STARTUP_SECONDS)

    def stop(self):
        for process in (self.frontend, self.api):
            if process is not None:
                process.stop()


@pytest.fixture
def deployment(tmp_path):
    running = Deployment(tmp_path)
    try:
        running.start_frontend()
        running.start_api()
        yield running
    finally:
        running.stop()


def test_two_separate_processes_communicate_only_over_http(deployment):
    assert deployment.frontend.pid != deployment.api.pid
    assert deployment.frontend.pid != os.getpid() and deployment.api.pid != os.getpid()
    assert deployment.frontend_port != deployment.api_port

    status, headers, body = fetch(deployment.frontend_origin + "/config.js")
    assert status == 200 and deployment.api_origin in body.decode()

    status, headers, body = fetch(deployment.api_origin + "/health", headers={"Origin": deployment.frontend_origin})
    assert status == 200 and json.loads(body) == {"status": "ok"}
    assert headers["access-control-allow-origin"] == deployment.frontend_origin

    status, headers, body = fetch(deployment.api_origin + "/api/nope", headers={"Origin": deployment.frontend_origin})
    assert status == 404 and json.loads(body)["error"]["code"] == "not_found"


def test_the_api_stays_alive_and_safe_when_its_database_is_unreachable(deployment):
    status, headers, body = fetch(deployment.api_origin + "/health/db", headers={"Origin": deployment.frontend_origin})

    assert status == 503
    assert json.loads(body) == {"status": "unavailable", "database": "unavailable"}
    assert headers["access-control-allow-origin"] == deployment.frontend_origin
    assert b"127.0.0.1" not in body and b"probe" not in body and b"cinema_process_probe" not in body
    assert deployment.api.running()
    assert fetch(deployment.api_origin + "/health")[0] == 200  # still serving afterwards
    log = deployment.api.output()
    assert "process-test-secret-key" not in log  # secrets are never logged


def test_stopping_the_api_leaves_the_frontend_serving_and_the_api_restarts_alone(deployment):
    frontend_pid = deployment.frontend.pid

    deployment.api.stop()

    wait_until_refused(deployment.api_port)
    for path in ("/index.html", "/config.js", "/assets/cinema.js"):
        assert fetch(deployment.frontend_origin + path)[0] == 200  # static pages do not need the API
    assert deployment.frontend.running() and deployment.frontend.pid == frontend_pid

    deployment.start_api()  # started again on its own, nothing else restarted

    assert fetch(deployment.api_origin + "/health")[0] == 200
    assert deployment.frontend.pid == frontend_pid


def test_stopping_the_frontend_leaves_the_api_running(deployment):
    api_pid = deployment.api.pid

    deployment.frontend.stop()

    wait_until_refused(deployment.frontend_port)
    assert fetch(deployment.api_origin + "/health")[0] == 200
    assert deployment.api.running() and deployment.api.pid == api_pid


def test_the_api_without_cors_configuration_grants_no_origin(tmp_path):
    running = Deployment(tmp_path, cors=False)
    try:
        running.start_api()
        status, headers, _ = fetch(running.api_origin + "/health", headers={"Origin": running.frontend_origin})
    finally:
        running.stop()

    assert status == 200
    assert "access-control-allow-origin" not in headers


# --- start-up failures are clear and safe -------------------------------------------------


def run_to_exit(args, env, timeout=30):
    return subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


@pytest.mark.parametrize("environ", [{"API_BASE_URL": "*"}, {"API_BASE_URL": "http://x/api"}, {"FRONTEND_PORT": "0"},
                                     {"FRONTEND_PORT": "abc"}])
def test_the_frontend_server_refuses_invalid_configuration(environ):
    result = run_to_exit([sys.executable, str(ROOT.parent / "frontend" / "server.py")], clean_environment(**environ))

    assert result.returncode == 2
    assert "invalid configuration" in result.stderr
    assert "Traceback" not in result.stderr


def test_the_frontend_server_reports_a_port_that_is_already_in_use():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen(1)
        port = busy.getsockname()[1]
        result = run_to_exit([sys.executable, str(ROOT.parent / "frontend" / "server.py")],
                             clean_environment(FRONTEND_PORT=str(port)))

    assert result.returncode == 1
    assert "cannot listen" in result.stderr
    assert "Traceback" not in result.stderr


def test_the_api_refuses_to_start_with_a_wildcard_cors_origin():
    env = clean_environment(SECRET_KEY="process-test-secret-key-not-a-real-one", DB_NAME="cinema_process_probe",
                            DB_USER="probe", DB_PORT="1", CORS_ALLOWED_ORIGINS="*")
    port = free_port()
    started = time.monotonic()
    result = run_to_exit([sys.executable, "-m", "flask", "--app", "app", "run", "--port", str(port),
                          "--no-reload", "--no-debugger"], env)

    assert result.returncode != 0
    assert "CORS_ALLOWED_ORIGINS" in result.stderr + result.stdout
    assert "process-test-secret-key" not in result.stderr + result.stdout
    assert is_refused(port)
    assert time.monotonic() - started < 30
