#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB="cinema_live_demo_$(date +%Y%m%d_%H%M%S)_$$"
createdb --template=template0 --encoding=UTF8 "$DB"
trap 'dropdb --if-exists "$DB"' EXIT
psql -X -v ON_ERROR_STOP=1 -d "$DB" -f "$HERE/../schema.sql" >/dev/null
psql -X -v ON_ERROR_STOP=1 -d "$DB" -f "$HERE/../seed.sql" >/dev/null
psql -X -v ON_ERROR_STOP=1 -d "$DB" -f "$HERE/live_demo.sql"
