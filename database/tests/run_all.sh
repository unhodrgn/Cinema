#!/usr/bin/env bash
# Runs the whole database verification on a NEW, uniquely named, DISPOSABLE database:
#   1. schema.sql  2. seed.sql  3. integrity_tests.sql  4. reconciliation_probes.sql
#   5. test_concurrency.py  6. test_application_role.py
# The database is created by this script and dropped at the end (only that one; set
# KEEP_DB=1 to keep it). It never touches any other database.
#
# Connection: libpq environment (PGHOST, PGPORT, PGUSER, PGPASSWORD). The role needs
# CREATEDB, CREATEROLE (temporary role test), and access to btree_gist.
# Python tests need psycopg2:  python -m pip install psycopg2-binary
#
#   bash database/tests/run_all.sh
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_DIR="$(cd "$HERE/.." && pwd)"
DB="cinema_test_$(date +%Y%m%d_%H%M%S)_$$"
PY="${PYTHON:-python}"
FAILED=0

step() { printf '\n=== %s\n' "$1"; }

if psql -X -Atqc "select 1 from pg_database where datname='$DB'" postgres | grep -q 1; then
  echo "Refusing: database $DB already exists"; exit 2
fi
step "create disposable database $DB"
createdb --template=template0 --encoding=UTF8 "$DB" || { echo "createdb failed"; exit 2; }

cleanup() { if [ "${KEEP_DB:-0}" != "1" ]; then dropdb --if-exists "$DB" >/dev/null 2>&1 && echo "dropped $DB"; else echo "kept $DB"; fi; }
trap cleanup EXIT

step "1. schema.sql";  psql -X -q -v ON_ERROR_STOP=1 -d "$DB" -f "$DB_DIR/schema.sql" >/dev/null && echo "OK" || { echo "FAILED"; exit 1; }
step "2. seed.sql";    psql -X -q -v ON_ERROR_STOP=1 -d "$DB" -f "$DB_DIR/seed.sql"   >/dev/null && echo "OK" || { echo "FAILED"; exit 1; }

step "3. integrity_tests.sql"
OUT=$(psql -X -v ON_ERROR_STOP=1 -d "$DB" -f "$DB_DIR/tests/integrity_tests.sql" 2>&1); RC=$?
echo "$OUT" | grep -E "ALL [0-9]+ CHECKS PASSED|ERROR" ; echo "exit=$RC"; [ $RC -ne 0 ] && FAILED=1

step "4. reconciliation_probes.sql"
OUT=$(psql -X -v ON_ERROR_STOP=1 -d "$DB" -f "$DB_DIR/tests/reconciliation_probes.sql" 2>&1); RC=$?
echo "$OUT" | grep -E "SUMMARY|MISMATCH|\[P16\]" ; echo "exit=$RC"; [ $RC -ne 0 ] && FAILED=1

step "5. test_concurrency.py"
PGDATABASE="$DB" "$PY" "$HERE/test_concurrency.py"; RC=$?; echo "exit=$RC"; [ $RC -ne 0 ] && FAILED=1

step "6. test_application_role.py"
PGDATABASE="$DB" "$PY" "$HERE/test_application_role.py"; RC=$?; echo "exit=$RC"; [ $RC -ne 0 ] && FAILED=1

echo
if [ $FAILED -eq 0 ]; then echo "ALL DATABASE TESTS PASSED"; else echo "DATABASE TESTS FAILED"; fi
exit $FAILED
