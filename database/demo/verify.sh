#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
demo=database/demo/demo.sh
date -u '+%Y-%m-%d %H:%M:%S UTC'
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git rev-parse HEAD
else
  printf '%s\n' 'Standalone submission package (database baseline: 121854a0e006d824dd4aba7274deec7524da9694)'
fi
psql --version
scratch=$(mktemp -d /tmp/cinema-member-a-test.XXXXXX)
dir=$(bash "$demo" setup)
cleanup() {
  bash "$demo" cleanup "$dir"
  rm -f "$scratch/a.log" "$scratch/b.log"
  rmdir "$scratch"
}
trap cleanup EXIT
for script in 01_inspect.sql 02_booking_lifecycle.sql 03_exceptions.sql 04_permissions.sql; do
  printf '\n=== %s ===\n' "$script"
  bash "$demo" run "$dir" "$script"
done
(
  printf '%s\n' '\i database/demo/05_concurrent_a.sql' 'SELECT pg_sleep(3);' 'COMMIT;' | PGAPPNAME=member_a_session_a bash "$demo" session "$dir"
) >"$scratch/a.log" 2>&1 &
a=$!
for n in {1..40}; do
  if grep -q 'winner_booking_id' "$scratch/a.log"; then break; fi
  sleep 0.05
done
grep -q winner_booking_id "$scratch/a.log"
PGAPPNAME=member_a_session_b bash "$demo" run "$dir" 05_concurrent_b.sql >"$scratch/b.log" 2>&1 &
b=$!
waiting=''
for n in {1..25}; do
  waiting=$(printf '%s\n' "\pset tuples_only on" "SELECT 'PASS B is waiting on A' FROM pg_stat_activity b JOIN pg_stat_activity a ON a.pid=ANY(pg_blocking_pids(b.pid)) WHERE b.application_name='member_a_session_b' AND a.application_name='member_a_session_a';" | bash "$demo" session "$dir")
  if [[ "$waiting" == *'PASS B is waiting on A'* ]]; then break; fi
  sleep 0.05
done
[[ "$waiting" == *'PASS B is waiting on A'* ]]
printf '\n=== Two-session lock observation ===\n%s\n' "$waiting"
wait "$a"
wait "$b"
cat "$scratch/a.log" "$scratch/b.log"
bash "$demo" run "$dir" 05_concurrent_verify.sql
grep -q UC002 "$scratch/b.log"
printf '\nALL LIVE DEMONSTRATIONS PASSED\n'
