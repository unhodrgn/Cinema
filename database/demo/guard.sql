\set ON_ERROR_STOP on
SELECT current_database() ~ '^cinema_test_[a-z0-9_]+$'
 AND EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.bookings'::regclass
             AND conname='bookings_total_amount_finite' AND convalidated) AS demo_ok \gset
\if :demo_ok
\else
  \echo '격리된 cinema_test_* 데이터베이스와 0004가 필요합니다.'
  SELECT 1 / 0;
\endif
