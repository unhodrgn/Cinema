#!/usr/bin/env bash
# Compatibility command. Select the disposable cluster explicitly.
set -eu
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export TEST_DB_PORT="${TEST_DB_PORT:-${PGPORT:?set TEST_DB_PORT or PGPORT explicitly}}"
export TEST_DB_HOST="${TEST_DB_HOST:-${PGHOST:-127.0.0.1}}"
export TEST_DB_ADMIN_USER="${TEST_DB_ADMIN_USER:-${PGUSER:-}}"
export TEST_DB_ADMIN_PASSWORD="${TEST_DB_ADMIN_PASSWORD:-${PGPASSWORD:-}}"
args=()
if [[ "${KEEP_DB:-0}" == "1" ]]; then args+=(--keep-db); fi
exec "${PYTHON:-python}" "$ROOT/backend/tests/run_database.py" "${args[@]}"
