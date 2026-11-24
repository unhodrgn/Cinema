#!/usr/bin/env python3
"""Concurrency tests for the Cinema database (real, separate PostgreSQL sessions).

Scenarios
  C1  8 sessions race for ONE seat               -> exactly 1 booking, 7 x UC002
  C2  explicit two-session lock proof            -> B blocks until A commits, then UC002
  C3  overlapping multi-seat requests            -> exactly 1 wins, loser leaves nothing
  C4  pay_booking vs expire_overdue_bookings at the exact deadline (N races)
                                                 -> final state always valid, never PAID late
  C5  pay_booking vs cancel_booking races        -> final state always valid
  C6  several expire_overdue_bookings() callers at once
                                                 -> each overdue booking expired exactly once

SAFETY: needs a NEW, DISPOSABLE database that has schema.sql + seed.sql applied and
NO bookings yet. It refuses to run otherwise. It leaves its bookings behind (bookings
are history and cannot be deleted), so use a fresh database for every run.
Connection: libpq env vars (PGHOST, PGPORT, PGUSER, PGPASSWORD); PGDATABASE is REQUIRED.
Requires: psycopg2 (psycopg2-binary). The role must own the tables (it creates them).
"""
import os
import random
import sys
import threading
import time

import psycopg2

DBNAME = os.environ.get("PGDATABASE")
RESULTS = []


def connect():
    return psycopg2.connect(dbname=DBNAME, connect_timeout=5)


def check(ok, label, detail=""):
    RESULTS.append((ok, label))
    print(("[PASS] " if ok else "[FAIL] ") + label + (f"  ({detail})" if detail else ""), flush=True)
    return ok


def one(conn, sql, args=None):
    with conn.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchone()[0]


def make_screening(conn, n, price=12000):
    """New far-future screening (room 1) per scenario; returns showtime_id."""
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO showtimes(movie_id, room_id, starts_at, ticket_price)
               SELECT (SELECT min(movie_id) FROM movies), (SELECT min(room_id) FROM theater_rooms),
                      date_trunc('hour', now()) + (200 + %s) * interval '1 day', %s
               RETURNING showtime_id""", (n, price))
        sid = cur.fetchone()[0]
    conn.commit()
    return sid


def seat_ids(conn, showtime_id, labels):
    with conn.cursor() as cur:
        cur.execute(
            """SELECT se.seat_row || se.seat_number, se.seat_id FROM showtimes s
               JOIN seats se ON se.room_id = s.room_id WHERE s.showtime_id = %s""", (showtime_id,))
        m = dict(cur.fetchall())
    conn.commit()
    return [m[x] for x in labels]


def customers(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT user_id FROM users WHERE role='CUSTOMER' ORDER BY user_id")
        ids = [r[0] for r in cur.fetchall()]
    conn.commit()
    return ids


def run_threads(targets):
    threads = [threading.Thread(target=t, daemon=True) for t in targets]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return all(not t.is_alive() for t in threads)


def book(user, showtime, seats, out, hold=0.0):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT create_booking(%s, %s, %s)", (user, showtime, seats))
            bid = cur.fetchone()[0]
        if hold:
            time.sleep(hold)
        conn.commit()
        out.append(("ok", bid))
    except psycopg2.Error as e:
        conn.rollback()
        out.append(("err", e.pgcode))
    finally:
        conn.close()


# ---------------------------------------------------------------------------
def c1_same_seat_race(ctl, cust):
    s = make_screening(ctl, 1)
    (a1,) = seat_ids(ctl, s, ["A1"])
    out = []
    ok = run_threads([lambda i=i: book(cust[i % len(cust)], s, [a1], out) for i in range(8)])
    wins = [o for o in out if o[0] == "ok"]
    errs = [o[1] for o in out if o[0] == "err"]
    check(ok, "C1 all 8 sessions finished (no deadlock / hang)")
    check(len(wins) == 1 and errs.count("UC002") == 7, "C1 exactly 1 booking wins, 7 rejected with UC002 (seat already reserved)", f"wins={len(wins)} errs={errs}")
    n = one(ctl, "SELECT count(*) FROM booking_seats bs JOIN bookings b USING (booking_id) WHERE b.showtime_id=%s AND bs.seat_id=%s AND b.status='BOOKED'", (s, a1))
    ctl.commit()
    check(n == 1, "C1 exactly one active seat allocation in the database", f"count={n}")


def c2_lock_proof(ctl, cust):
    s = make_screening(ctl, 2)
    (a1,) = seat_ids(ctl, s, ["A1"])
    out_b, started, done = [], threading.Event(), threading.Event()
    conn_a = connect()
    with conn_a.cursor() as cur:  # A: booking + seat, transaction left OPEN
        cur.execute("SELECT create_booking(%s, %s, %s)", (cust[0], s, [a1]))
    def b():
        started.set()
        book(cust[1], s, [a1], out_b)
        done.set()
    t = threading.Thread(target=b, daemon=True)
    t.start()
    started.wait(5)
    time.sleep(1.5)
    check(not done.is_set(), "C2 session B is BLOCKED on the lock while A has not committed")
    conn_a.commit()
    conn_a.close()
    t.join(15)
    check(out_b == [("err", "UC002")], "C2 after A commits, B is rejected with UC002", str(out_b))


def c3_multiseat_overlap(ctl, cust):
    s = make_screening(ctl, 3)
    a2, a3, a4 = seat_ids(ctl, s, ["A2", "A3", "A4"])
    out = []
    run_threads([lambda: book(cust[0], s, [a2, a3], out), lambda: book(cust[1], s, [a3, a4], out)])
    wins = [o for o in out if o[0] == "ok"]
    check(len(wins) == 1 and [o[1] for o in out if o[0] == "err"] == ["UC002"], "C3 exactly one of two overlapping multi-seat bookings wins", str(out))
    held = one(ctl, "SELECT count(*) FROM booking_seats bs JOIN bookings b USING (booking_id) WHERE b.showtime_id=%s", (s,))
    nb = one(ctl, "SELECT count(*) FROM bookings WHERE showtime_id=%s", (s,))
    ctl.commit()
    check(nb == 1 and held == 2, "C3 loser left nothing behind (1 booking, 2 seat rows)", f"bookings={nb} seat_rows={held}")


def set_deadlines(ids, ms_from_now):
    """Committed helper: put every booking's expires_at at the same instant (tests only)."""
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE bookings DISABLE TRIGGER USER")
        cur.execute("SELECT clock_timestamp() + %s * interval '1 millisecond'", (ms_from_now,))
        t0 = cur.fetchone()[0]
        cur.execute("SELECT clock_timestamp()")
        db_now = cur.fetchone()[0]
        py_now = time.time()
        cur.execute("UPDATE bookings SET booked_at = %s - interval '10 minutes', expires_at = %s WHERE booking_id = ANY(%s)", (t0, t0, ids))
        cur.execute("ALTER TABLE bookings ENABLE TRIGGER USER")
    conn.commit()
    conn.close()
    return py_now + (t0 - db_now).total_seconds()


def c4_pay_vs_expire(ctl, cust, n=40):
    s = make_screening(ctl, 4)
    seats = seat_ids(ctl, s, [f"{r}{i}" for r in "ABCDE" for i in range(1, 9)])[:n]
    ids = []
    for i, seat in enumerate(seats):
        out = []
        book(cust[i % len(cust)], s, [seat], out)
        ids.append(out[0][1])
    deadline_py = set_deadlines(ids, 2500)
    pay_result = {}
    stop_at = deadline_py + 0.5

    def payer(bid, user):
        conn = connect()                      # connect BEFORE waiting so the call lands at the deadline
        time.sleep(max(0, deadline_py + random.uniform(-0.08, 0.03) - time.time()))
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT pay_booking(%s, %s)", (bid, user))
                pay_result[bid] = cur.fetchone()[0]
            conn.commit()
        except psycopg2.Error as e:
            conn.rollback()
            pay_result[bid] = "ERR:" + str(e.pgcode)
        finally:
            conn.close()

    def expirer():
        conn = connect()
        while time.time() < stop_at:
            with conn.cursor() as cur:
                cur.execute("SELECT expire_overdue_bookings()")
            conn.commit()
            time.sleep(random.uniform(0, 0.004))
        conn.close()

    users = {}
    with ctl.cursor() as cur:
        cur.execute("SELECT booking_id, user_id FROM bookings WHERE booking_id = ANY(%s)", (ids,))
        users = dict(cur.fetchall())
    ctl.commit()
    targets = [lambda b=b: payer(b, users[b]) for b in ids] + [expirer, expirer]
    check(run_threads(targets), f"C4 {n} payers + 2 expirers finished (no deadlock / hang)")
    # final expire after the deadline so nothing overdue is left pending, then verify every booking
    one(ctl, "SELECT expire_overdue_bookings()"); ctl.commit()
    bad, paid, expired = [], 0, 0
    with ctl.cursor() as cur:
        cur.execute(
            """SELECT b.booking_id, b.status, b.payment_status, b.paid_at, b.expires_at,
                      (SELECT count(*) FROM booking_seats bs WHERE bs.booking_id=b.booking_id)
               FROM bookings b WHERE b.booking_id = ANY(%s)""", (ids,))
        for bid, st, ps, paid_at, exp_at, nseats in cur.fetchall():
            res = pay_result.get(bid)
            if st == "BOOKED" and ps == "PAID" and nseats == 1 and paid_at is not None and paid_at < exp_at and res == "PAID":
                paid += 1
            elif st == "EXPIRED" and ps == "UNPAID" and nseats == 0 and paid_at is None and res in ("EXPIRED", "ERR:UC006"):
                expired += 1
            else:
                bad.append((bid, st, ps, nseats, paid_at, exp_at, res))
    ctl.commit()
    check(not bad, "C4 every booking ended in a VALID state (PAID+seat+paid_at<expires_at, or EXPIRED+UNPAID+no seats)", f"invalid={bad[:3]}")
    check(paid + expired == len(ids), f"C4 outcome split under the race: PAID={paid}, EXPIRED={expired}")
    check(paid > 0 and expired > 0, "C4 the race was real: both outcomes occurred (payment won some, expiry won others)")


def c5_pay_vs_cancel(ctl, cust, n=20):
    s = make_screening(ctl, 5)
    seats = seat_ids(ctl, s, [f"{r}{i}" for r in "ABCDE" for i in range(1, 5)])[:n]
    jobs = []
    for i, seat in enumerate(seats):
        out = []
        book(cust[0], s, [seat], out)
        jobs.append(out[0][1])
    res = {}

    def op(kind, bid):
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT {kind}_booking(%s, %s)", (bid, cust[0]))
                res[(kind, bid)] = cur.fetchone()[0]
            conn.commit()
        except psycopg2.Error as e:
            conn.rollback()
            res[(kind, bid)] = "ERR:" + str(e.pgcode)
        finally:
            conn.close()

    targets = []
    for bid in jobs:
        targets += [lambda b=bid: op("pay", b), lambda b=bid: op("cancel", b)]
    check(run_threads(targets), f"C5 {n} pay/cancel pairs finished (no deadlock / hang)")
    bad = []
    with ctl.cursor() as cur:
        cur.execute(
            """SELECT b.booking_id, b.status, b.payment_status,
                      (SELECT count(*) FROM booking_seats bs WHERE bs.booking_id=b.booking_id)
               FROM bookings b WHERE b.booking_id = ANY(%s)""", (jobs,))
        for bid, st, ps, nseats in cur.fetchall():
            pay, can = res[("pay", bid)], res[("cancel", bid)]
            ok = (st == "CANCELLED" and nseats == 0 and can == "CANCELLED" and
                  ((ps == "PAID" and pay == "PAID") or (ps == "UNPAID" and pay == "ERR:UC006")))
            if not ok:
                bad.append((bid, st, ps, nseats, pay, can))
    ctl.commit()
    check(not bad, "C5 every booking ended CANCELLED with no seats; PAID iff the payment won", f"invalid={bad[:3]}")


def c6_parallel_expirers(ctl, cust, n=20):
    s = make_screening(ctl, 6)
    seats = seat_ids(ctl, s, [f"{r}{i}" for r in "ABCDE" for i in range(1, 5)])[:n]
    ids = []
    for seat in seats:
        out = []
        book(cust[0], s, [seat], out)
        ids.append(out[0][1])
    set_deadlines(ids, -2000)  # all overdue already
    counts = []

    def expirer():
        conn = connect()
        with conn.cursor() as cur:
            cur.execute("SELECT expire_overdue_bookings()")
            counts.append(cur.fetchone()[0])
        conn.commit()
        conn.close()

    check(run_threads([expirer] * 5), "C6 5 parallel expire_overdue_bookings() callers finished")
    # rows locked by a peer are skipped by design; a final sweep must find nothing left over
    leftover = one(ctl, "SELECT expire_overdue_bookings()"); ctl.commit()
    total = sum(counts) + leftover
    states = one(ctl, "SELECT count(*) FROM bookings WHERE booking_id = ANY(%s) AND status='EXPIRED' AND payment_status='UNPAID'", (ids,))
    seatrows = one(ctl, "SELECT count(*) FROM booking_seats WHERE booking_id = ANY(%s)", (ids,))
    ctl.commit()
    check(total == len(ids), f"C6 each overdue booking expired exactly once (sum of counts = {total})", f"counts={counts}+{leftover}")
    check(states == len(ids) and seatrows == 0, "C6 all EXPIRED + UNPAID, all seat rows deleted")


def c7_isolation_levels(ctl, cust):
    for offset, level in enumerate(("READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE")):
        screening = make_screening(ctl, 70 + offset)
        seat, extra = seat_ids(ctl, screening, ["A1", "A2"])
        old = connect()
        try:
            old.set_session(isolation_level=level)
            assert one(old, "SELECT count(*) FROM bookings WHERE showtime_id=%s", (screening,)) == 0
            assert one(ctl, "SELECT create_booking(%s,%s,%s)", (cust[0], screening, [seat]))
            ctl.commit()
            try:
                one(old, "SELECT create_booking(%s,%s,%s)", (cust[1], screening, [extra, seat]))
                old.commit()
                code = None
            except psycopg2.Error as exc:
                code = exc.pgcode
                old.rollback()
            allowed = {"UC002"} if level == "READ COMMITTED" else {"UC002", "40001"}
            check(code in allowed, f"C7 {level} rejects the second allocation", str(code))
            if code == "40001":
                try:
                    one(old, "SELECT create_booking(%s,%s,%s)", (cust[1], screening, [extra, seat]))
                    old.commit()
                    retry_code = None
                except psycopg2.Error as exc:
                    retry_code = exc.pgcode
                    old.rollback()
                check(retry_code == "UC002", f"C7 {level} fresh-transaction retry sees the seat conflict")
            count = one(ctl, "SELECT count(*) FROM booking_seats WHERE showtime_id=%s", (screening,))
            parents = one(ctl, "SELECT count(*) FROM bookings WHERE showtime_id=%s", (screening,))
            ctl.commit()
            check(count == parents == 1, f"C7 {level} loser left no booking or allocation")
        finally:
            old.close()


def wait_for_blocker(observer, blocked_pid, holder_pid):
    """Observe a real lock wait instead of assuming the thread has reached SQL."""
    until = time.monotonic() + 3
    while time.monotonic() < until:
        blocked = one(observer, "SELECT %s = ANY(pg_blocking_pids(%s))", (holder_pid, blocked_pid))
        observer.commit()
        if blocked:
            return True
        time.sleep(0.01)
    return False


def run_operation(conn, statement, args, result):
    try:
        value = one(conn, statement, args)
        conn.commit()
        result.append(("ok", value))
    except psycopg2.Error as exc:
        conn.rollback()
        result.append(("err", exc.pgcode))


def booking_state(conn, booking):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT status, payment_status, (SELECT count(*) FROM booking_seats WHERE booking_id=b.booking_id)
            FROM bookings b WHERE booking_id=%s
        """, (booking,))
        state = cur.fetchone()
    conn.commit()
    return state


def c8_deadline_after_lock(ctl, cust):
    for offset, operation in enumerate(("pay_booking", "cancel_booking")):
        screening = make_screening(ctl, 80 + offset)
        (seat,) = seat_ids(ctl, screening, ["B1"])
        booking = one(ctl, "SELECT create_booking(%s,%s,%s)", (cust[0], screening, [seat]))
        ctl.commit()
        holder, caller = connect(), connect()
        result = []
        try:
            set_deadlines([booking], 2000)
            deadline = one(holder, "SELECT expires_at FROM bookings WHERE booking_id=%s FOR NO KEY UPDATE",
                           (booking,))
            thread = threading.Thread(
                target=run_operation, args=(caller, f"SELECT {operation}(%s,%s)", (booking, cust[0]), result),
                daemon=True,
            )
            thread.start()
            blocked = wait_for_blocker(ctl, caller.get_backend_pid(), holder.get_backend_pid())
            before = one(ctl, "SELECT clock_timestamp() < %s", (deadline,))
            check(blocked and before, f"C8 {operation} is waiting before the deadline")
            # Sleep using the database clock, then release the row.
            one(ctl, "SELECT pg_sleep(greatest(0, extract(epoch FROM (%s - clock_timestamp())) + 0.02))",
                (deadline,))
            ctl.commit()
            holder.rollback()
            thread.join(8)
            check(result == [("ok", "EXPIRED")], f"C8 {operation} commits expiration after waiting", str(result))
            check(booking_state(ctl, booking) == ("EXPIRED", "UNPAID", 0),
                  f"C8 {operation} retains expired history and releases the seat")
            check(one(ctl, "SELECT create_booking(%s,%s,%s)", (cust[1], screening, [seat])) is not None,
                  f"C8 {operation} released seat is bookable")
            ctl.commit()
        finally:
            holder.close()
            caller.close()


def c9_availability_lock(ctl, cust):
    for offset, action in enumerate(("availability", "create", "paid", "timeout")):
        screening = make_screening(ctl, 90 + offset)
        (seat,) = seat_ids(ctl, screening, ["C1"])
        booking = one(ctl, "SELECT create_booking(%s,%s,%s)", (cust[0], screening, [seat]))
        ctl.commit()
        if action != "paid":
            set_deadlines([booking], -1000)
        holder, caller = connect(), connect()
        result = []
        try:
            one(holder, "SELECT 1 FROM bookings WHERE booking_id=%s FOR NO KEY UPDATE", (booking,))
            if action == "paid":
                assert one(holder, "SELECT pay_booking(%s,%s)", (booking, cust[0])) == "PAID"
            if action == "create":
                statement, args = "SELECT create_booking(%s,%s,%s)", (cust[1], screening, [seat])
            else:
                statement = "SELECT is_available FROM screening_seat_availability(%s) WHERE seat_id=%s"
                args = screening, seat
            thread = threading.Thread(target=run_operation, args=(caller, statement, args, result), daemon=True)
            thread.start()
            check(wait_for_blocker(ctl, caller.get_backend_pid(), holder.get_backend_pid()),
                  f"C9 {action} waits on the relevant booking")
            if action == "timeout":
                thread.join(8)
                check(result == [("err", "55P03")], "C9 lock timeout is retryable, no false availability", str(result))
                holder.rollback()
                check(one(ctl, statement, args) is True, "C9 new transaction resolves expiry after timeout")
                ctl.commit()
            else:
                if action == "paid":
                    holder.commit()
                else:
                    holder.rollback()
                thread.join(8)
                if action == "create":
                    valid = len(result) == 1 and result[0][0] == "ok" and isinstance(result[0][1], int)
                else:
                    valid = result == [("ok", action == "availability")]
                check(valid, f"C9 {action} uses the state after acquiring the lock", str(result))
            expected = ("BOOKED", "PAID", 1) if action == "paid" else ("EXPIRED", "UNPAID", 0)
            check(booking_state(ctl, booking) == expected, f"C9 {action} leaves a consistent parent and seat state")
        finally:
            holder.close()
            caller.close()


def c10_screening_update_race(ctl, cust):
    for offset, level in enumerate(("READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE")):
        screening = make_screening(ctl, 100 + offset)
        (seat,) = seat_ids(ctl, screening, ["D1"])
        editor, observer = connect(), connect()
        result = []
        try:
            editor.set_session(isolation_level=level)
            one(editor, "SELECT ticket_price FROM showtimes WHERE showtime_id=%s", (screening,))
            one(ctl, "SELECT create_booking(%s,%s,%s)", (cust[0], screening, [seat]))
            run_operation_sql = "UPDATE showtimes SET ticket_price=1 WHERE showtime_id=%s RETURNING ticket_price"
            thread = threading.Thread(target=run_operation, args=(editor, run_operation_sql, (screening,), result),
                                      daemon=True)
            thread.start()
            check(wait_for_blocker(observer, editor.get_backend_pid(), ctl.get_backend_pid()),
                  f"C10 {level} editor waits for the first booking")
            ctl.commit()
            thread.join(8)
            expected = "UC001" if level == "READ COMMITTED" else "40001"
            check(result == [("err", expected)], f"C10 {level} D2 protects the first booking", str(result))
            check(one(ctl, "SELECT ticket_price FROM showtimes WHERE showtime_id=%s", (screening,)) == 12000,
                  f"C10 {level} booked screening price stayed unchanged")
            ctl.commit()
        finally:
            ctl.rollback()
            editor.close()
            observer.close()


def c11_global_and_scoped_expiry(ctl, cust):
    screening = make_screening(ctl, 110)
    first_seat, second_seat = seat_ids(ctl, screening, ["E1", "E2"])
    first = one(ctl, "SELECT create_booking(%s,%s,%s)", (cust[0], screening, [first_seat]))
    second = one(ctl, "SELECT create_booking(%s,%s,%s)", (cust[1], screening, [second_seat]))
    ctl.commit()
    set_deadlines([first, second], -1000)
    holder, reader = connect(), connect()
    result = []
    try:
        one(holder, "SELECT 1 FROM bookings WHERE booking_id=%s FOR NO KEY UPDATE", (first,))
        thread = threading.Thread(
            target=run_operation,
            args=(reader, "SELECT count(*) FROM screening_seat_availability(%s) WHERE is_available",
                  (screening,), result),
            daemon=True,
        )
        thread.start()
        check(wait_for_blocker(ctl, reader.get_backend_pid(), holder.get_backend_pid()),
              "C11 scoped reader waits on the first booking")
        check(one(ctl, "SELECT expire_overdue_bookings()") == 1,
              "C11 global expiry skips the locked row and processes the other")
        ctl.commit()
        holder.rollback()
        thread.join(8)
        check(result == [("ok", 50)], "C11 scoped reader resolves the row skipped by global expiry", str(result))
        check(all(booking_state(ctl, booking) == ("EXPIRED", "UNPAID", 0) for booking in (first, second)),
              "C11 both expiration paths retained history and left no allocations")
    finally:
        holder.close()
        reader.close()


def main():
    if not DBNAME:
        print("Set PGDATABASE to a disposable database (refusing to guess).")
        return 2
    ctl = connect()
    if one(ctl, "SELECT count(*) FROM bookings") != 0 or one(ctl, "SELECT count(*) FROM showtimes") != 140:
        print("Refusing to run: database must be freshly seeded (140 screenings) with no bookings.")
        return 2
    ctl.commit()
    cust = customers(ctl)
    if len(cust) < 2:
        print("Need two CUSTOMER accounts.")
        return 2
    print(f"Database: {DBNAME}; customers {cust}")
    for fn in (
        c1_same_seat_race, c2_lock_proof, c3_multiseat_overlap, c4_pay_vs_expire,
        c5_pay_vs_cancel, c6_parallel_expirers, c7_isolation_levels, c8_deadline_after_lock,
        c9_availability_lock, c10_screening_update_race, c11_global_and_scoped_expiry,
    ):
        try:
            fn(ctl, cust)
        except Exception as exc:  # report, continue
            check(False, f"{fn.__name__} raised {type(exc).__name__}", str(exc).strip().splitlines()[0])
            ctl.rollback()
    ctl.close()
    passed = sum(1 for ok, _ in RESULTS if ok)
    print(f"\nRESULT: {passed}/{len(RESULTS)} checks passed")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
