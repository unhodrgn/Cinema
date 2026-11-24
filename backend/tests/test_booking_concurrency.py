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


def main():
    if not DBNAME:
        print("Set PGDATABASE to a disposable database (refusing to guess).")
        return 2
    ctl = connect()
    if one(ctl, "SELECT count(*) FROM bookings") != 0 or one(ctl, "SELECT count(*) FROM showtimes") != 280:
        print("Refusing to run: database must be freshly seeded (280 screenings) with no bookings.")
        return 2
    ctl.commit()
    cust = customers(ctl)
    if len(cust) < 2:
        print("Need two CUSTOMER accounts.")
        return 2
    print(f"Database: {DBNAME}; customers {cust}")
    for fn in (c1_same_seat_race, c2_lock_proof, c3_multiseat_overlap, c4_pay_vs_expire, c5_pay_vs_cancel, c6_parallel_expirers):
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
