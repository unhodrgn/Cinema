-- Account IDs are unique ignoring case. The API stores them NFKC-normalized and trimmed
-- (app.api.v1.auth.normalize_username) and compares lower(username) on login, so
-- 'Customer1', ' customer1 ' and the full-width 'ｃｕｓｔｏｍｅｒ１' are all the same account ID as 'customer1'.
-- This migration does not modify data: it stops, naming the rows, if existing data would
-- break the rule, so they can be reconciled by hand first.
BEGIN;
SET LOCAL lock_timeout = '5s';
LOCK TABLE users IN ACCESS EXCLUSIVE MODE;

DO $$
DECLARE
 duplicate_ids bigint;
 unnormalized_ids bigint;
BEGIN
 SELECT count(*) INTO duplicate_ids FROM (
  SELECT lower(username) FROM users GROUP BY lower(username) HAVING count(*) > 1) d;
 IF duplicate_ids > 0 THEN
  RAISE EXCEPTION USING ERRCODE = '23505',
   MESSAGE = format('Migration 0005 stopped: %s account ID(s) differ only by letter case', duplicate_ids),
   HINT = 'Reconcile the duplicate accounts (SELECT lower(username), array_agg(user_id) FROM users GROUP BY 1 HAVING count(*) > 1) before retrying; this migration does not modify data.';
 END IF;

 -- An ID with surrounding spaces or a non-NFKC form could never be typed at login again.
 SELECT count(*) INTO unnormalized_ids FROM users
  WHERE username <> btrim(username) OR username IS NOT NFKC NORMALIZED;
 IF unnormalized_ids > 0 THEN
  RAISE EXCEPTION USING ERRCODE = '23514',
   MESSAGE = format('Migration 0005 stopped: %s account ID(s) are not trimmed NFKC text', unnormalized_ids),
   HINT = 'Rename them (SELECT user_id, username FROM users WHERE username <> btrim(username) OR username IS NOT NFKC NORMALIZED) before retrying; this migration does not modify data.';
 END IF;
END $$;

CREATE UNIQUE INDEX users_username_lower_key ON users (lower(username));
COMMIT;
