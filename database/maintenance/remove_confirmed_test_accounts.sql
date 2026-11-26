-- One-time data maintenance. Execute only on a verified copy, or with explicit
-- authorization during deployment. Do not include in automatic migrations.
BEGIN;
SET LOCAL lock_timeout = '5s';
LOCK TABLE public.users, public.bookings IN ACCESS EXCLUSIVE MODE;

DO $$
DECLARE
    deleted_count bigint;
BEGIN
    IF (SELECT count(*) FROM public.users WHERE role = 'CUSTOMER'
        AND ((user_id = 7 AND username = '!!!!!n')
          OR (user_id = 9 AND username = 'c u s t o m e r'))) <> 2
        OR EXISTS (SELECT 1 FROM public.bookings WHERE user_id IN (7, 9))
        OR (SELECT count(*) FROM pg_constraint
            WHERE confrelid = 'public.users'::regclass AND contype = 'f') <> 1
        OR NOT EXISTS (SELECT 1 FROM pg_constraint
            WHERE confrelid = 'public.users'::regclass AND contype = 'f'
              AND conrelid = 'public.bookings'::regclass AND conname = 'bookings_user_id_fkey'
              AND confdeltype IN ('a', 'r'))
        OR EXISTS (SELECT 1 FROM pg_trigger
            WHERE tgrelid = 'public.users'::regclass AND NOT tgisinternal)
    THEN
        RAISE EXCEPTION 'Expected account identities or dependency checks failed; no accounts deleted';
    END IF;

    DELETE FROM public.users WHERE role = 'CUSTOMER'
        AND ((user_id = 7 AND username = '!!!!!n')
          OR (user_id = 9 AND username = 'c u s t o m e r'));
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    IF deleted_count <> 2 THEN
        RAISE EXCEPTION 'Expected exactly two deletions, got %', deleted_count;
    END IF;
END $$;
COMMIT;
