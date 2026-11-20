#!/usr/bin/env python3
"""Verify the deployment grants with a throwaway role in a disposable database."""
import os
from pathlib import Path
import subprocess
import uuid

import psycopg2
from psycopg2 import sql


def run(cur, statement, args=None):
    cur.execute(statement, args)
    return cur.fetchone()[0]


def reject(cur, statement, args=None):
    cur.execute("SAVEPOINT permissions_probe")
    try:
        cur.execute(statement, args)
    except psycopg2.errors.InsufficientPrivilege:
        cur.execute("ROLLBACK TO SAVEPOINT permissions_probe")
    else:
        raise AssertionError(f"Expected permission denied: {statement}")
    finally:
        cur.execute("RELEASE SAVEPOINT permissions_probe")


def main():
    db = os.environ.get("PGDATABASE", "")
    if not db.startswith("cinema_test_"):
        raise SystemExit("Use a newly created disposable cinema_test_* database.")

    role = f"cinema_test_app_{uuid.uuid4().hex}"
    role_ident = sql.Identifier(role)
    grants = Path(__file__).resolve().parents[1] / "grant_application_role.sql"
    conn = psycopg2.connect(dbname=db, connect_timeout=5)
    try:
        with conn, conn.cursor() as cur:
            assert run(cur, "SHOW server_encoding") == "UTF8"
            cur.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(role_ident))
        subprocess.run(
            ["psql", "-X", "-q", "-v", f"app_role={role}", "-d", db, "-f", str(grants)],
            check=True,
        )
        with conn.cursor() as cur:
            cur.execute(sql.SQL("SET LOCAL ROLE {}").format(role_ident))
            user = run(cur, "INSERT INTO users(username,password_hash) VALUES (%s,%s) RETURNING user_id",
                       ("permission_probe", "test hash fixture"))
            assert run(cur, "SELECT role FROM users WHERE user_id=%s", (user,)) == "CUSTOMER"
            movie = run(cur, "INSERT INTO movies(title,duration_minutes) VALUES ('probe',90) RETURNING movie_id")
            cur.execute("UPDATE movies SET genre='probe' WHERE movie_id=%s", (movie,))
            screening = run(cur, """
                INSERT INTO showtimes(movie_id,room_id,starts_at,ticket_price)
                SELECT %s, min(room_id), now()+interval '400 days', 12000 FROM theater_rooms
                RETURNING showtime_id
            """, (movie,))
            cur.execute("UPDATE showtimes SET ticket_price=100 WHERE showtime_id=%s", (screening,))
            seat = run(cur, "SELECT seat_id FROM screening_seat_availability(%s) WHERE is_available LIMIT 1",
                       (screening,))
            booking = run(cur, "SELECT create_booking(%s,%s,ARRAY[%s]::bigint[])", (user, screening, seat))
            cur.execute("SET CONSTRAINTS ALL IMMEDIATE")
            cur.execute("SET CONSTRAINTS ALL DEFERRED")
            assert run(cur, "SELECT pay_booking(%s,%s)", (booking, user)) == "PAID"
            assert run(cur, "SELECT cancel_booking(%s,%s)", (booking, user)) == "CANCELLED"
            assert run(cur, "SELECT status FROM bookings WHERE booking_id=%s", (booking,)) == "CANCELLED"
            assert run(cur, "SELECT count(*) FROM booking_seats WHERE booking_id=%s", (booking,)) == 0
            run(cur, "SELECT expire_overdue_bookings()")
            reject(cur, "DELETE FROM bookings WHERE booking_id=%s", (booking,))
            reject(cur, "TRUNCATE bookings, booking_seats")
            reject(cur, "UPDATE bookings SET status='CANCELLED' WHERE booking_id=%s", (booking,))
            reject(cur, "INSERT INTO bookings(user_id,showtime_id,total_amount) VALUES (%s,%s,0)", (user, screening))
            reject(cur, "DELETE FROM booking_seats WHERE booking_id=%s", (booking,))
            reject(cur, "SELECT expire_locked_showtime_bookings(%s)", (screening,))
            reject(cur, "INSERT INTO users(username,password_hash,role) VALUES ('bad','fixture','ADMIN')")
            reject(cur, "UPDATE users SET role='ADMIN' WHERE user_id=%s", (user,))
            reject(cur, "UPDATE seats SET room_id=room_id WHERE seat_id=%s", (seat,))
            reject(cur, "CREATE TABLE public.permission_probe (id bigint)")
        print("[PASS] Application role can run approved operations and cannot write protected data directly.")
    finally:
        conn.rollback()
        with conn, conn.cursor() as cur:
            if run(cur, "SELECT EXISTS(SELECT FROM pg_roles WHERE rolname=%s)", (role,)):
                cur.execute(sql.SQL("DROP OWNED BY {}").format(role_ident))
                cur.execute(sql.SQL("DROP ROLE {}").format(role_ident))
        conn.close()


if __name__ == "__main__":
    main()
