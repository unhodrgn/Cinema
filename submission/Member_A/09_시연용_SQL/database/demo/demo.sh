#!/usr/bin/env bash
# Run from any directory. All connections go to a temporary private Unix socket.
set -euo pipefail
demo_dir=$(cd "$(dirname "$0")" && pwd)
repo_dir=$(cd "$demo_dir/../.." && pwd)
action=${1:-}
unset PGSERVICE PGSERVICEFILE PGHOSTADDR PGDATABASE PGOPTIONS PGPASSWORD PGCLIENTENCODING
export PGPORT=59486 PGUSER=cinema_demo_owner

case "$action" in
  setup)
    umask 077
    PGHOST=$(mktemp -d /tmp/cinema-live.XXXXXX)
    export PGHOST
    trap 'if [[ -f "$PGHOST/pg/postmaster.pid" ]]; then pg_ctl -D "$PGHOST/pg" stop -m fast >&2 || true; fi' EXIT
    initdb -D "$PGHOST/pg" -U "$PGUSER" -A trust --encoding=UTF8 --no-locale >&2
    pg_ctl -D "$PGHOST/pg" -l "$PGHOST/server.log" \
      -o "-k $PGHOST -p $PGPORT -c listen_addresses='' -c cinema_demo.isolated=on -c timezone=Asia/Seoul" start >&2
    createdb --template=template0 --encoding=UTF8 cinema_live_demo
    export PGDATABASE=cinema_live_demo
    (
      cd "$repo_dir"
      psql -X -v ON_ERROR_STOP=1 -f database/schema.sql -f database/seed.sql
      psql -X -v ON_ERROR_STOP=1 -c 'CREATE ROLE cinema_demo_app NOLOGIN'
      psql -X -v ON_ERROR_STOP=1 -v app_role=cinema_demo_app -f database/grant_application_role.sql
      psql -X -v ON_ERROR_STOP=1 -f database/demo/00_guard.sql
    ) >&2
    printf '%s\n' "$PGHOST"
    trap - EXIT
    ;;
  run|session|cleanup)
    supplied=${2:?Supply the directory printed by setup}
    PGHOST=$(cd "$supplied" && pwd -P)
    export PGHOST PGDATABASE=cinema_live_demo
    case "$PGHOST" in /tmp/cinema-live.*|/private/tmp/cinema-live.*) ;; *) exit 2 ;; esac
    [[ -O "$PGHOST" && -S "$PGHOST/.s.PGSQL.$PGPORT" && -f "$PGHOST/pg/PG_VERSION" ]]
    cd "$repo_dir"
    psql -X -q -v ON_ERROR_STOP=1 -f database/demo/00_guard.sql
    if [[ "$action" == cleanup ]]; then
      dropdb cinema_live_demo
      pg_ctl -D "$PGHOST/pg" stop -m fast
      printf 'Disposable database dropped; temporary cluster stopped at %s\n' "$PGHOST"
    elif [[ "$action" == session ]]; then
      exec psql -X -v ON_ERROR_STOP=1
    else
      script=${3:?Supply a demonstration script basename}
      case "$script" in
        01_inspect.sql|02_booking_lifecycle.sql|03_exceptions.sql|04_permissions.sql|05_concurrent_a.sql|05_concurrent_b.sql|05_concurrent_verify.sql)
          exec psql -X -v ON_ERROR_STOP=1 -f "$demo_dir/$script" ;;
        *) exit 2 ;;
      esac
    fi
    ;;
  *) printf 'Usage: %s setup | run DIR SCRIPT | session DIR | cleanup DIR\n' "$0" >&2; exit 2 ;;
esac
