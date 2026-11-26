"""Upgrade migration tests (0001 -> 0003 -> 0004), check_schema preflight, and lock timeout handling.

Runs strictly against disposable PostgreSQL databases created and dropped by this module.
"""

from decimal import Decimal
import os

import psycopg2
from psycopg2.extras import RealDictCursor
import pytest

import disposable_db
from app import create_app
from app.core.database import transaction
from scripts.check_schema import missing_objects

MIGRATIONS = disposable_db.BACKEND_DIR / "migrations"
M0001 = MIGRATIONS / "0001_baseline.sql"
M0003 = MIGRATIONS / "0003_booking_integrity.sql"
M0004 = MIGRATIONS / "0004_finite_money.sql"


def _create_db(postgres_settings, sql_files):
    forbidden = disposable_db.read_forbidden_names(os.environ, {})
    db = disposable_db.DisposableDatabase(postgres_settings, forbidden_names=forbidden)
    db.create()
    try:
        for path in sql_files:
            db.apply_sql_file(path)
    except Exception:
        db.drop()
        raise
    return db


def test_upgrade_0001_to_0003_to_0004_preserves_history_and_passes_check_schema(postgres_settings):
    db = _create_db(postgres_settings, (M0001, disposable_db.SEED_PATH))
    try:
        conn = db.connect()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                missing_before = missing_objects(cur)
                assert any("booking_seats_showtime_seat_key" in item for item in missing_before)
                assert any("showtimes_ticket_price_finite" in item for item in missing_before)
                assert any("numeric(12,2)" in item for item in missing_before)

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT showtime_id, room_id FROM showtimes "
                    "WHERE starts_at > now() + interval '1 day' ORDER BY showtime_id LIMIT 1"
                )
                showtime_id, room_id = cur.fetchone()
                cur.execute("SELECT seat_id FROM seats WHERE room_id = %s ORDER BY seat_id LIMIT 3", (room_id,))
                seats = [r[0] for r in cur.fetchall()]
                cur.execute("SELECT user_id FROM users WHERE role = 'CUSTOMER' ORDER BY user_id LIMIT 1")
                customer_id = cur.fetchone()[0]

                cur.execute("SELECT create_booking(%s, %s, %s)", (customer_id, showtime_id, seats[:2]))
                active_id = cur.fetchone()[0]
                cur.execute("SELECT create_booking(%s, %s, %s)", (customer_id, showtime_id, [seats[2]]))
                cancelled_id = cur.fetchone()[0]
                cur.execute("SELECT pay_booking(%s, %s)", (cancelled_id, customer_id))
                cur.execute("SELECT cancel_booking(%s, %s)", (cancelled_id, customer_id))
            conn.commit()
        finally:
            conn.close()

        db.apply_sql_file(M0003)
        db.apply_sql_file(M0004)

        conn = db.connect()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                assert missing_objects(cur) == []

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT booking_id, status, payment_status, total_amount FROM bookings ORDER BY booking_id"
                )
                rows = cur.fetchall()
                assert rows == [
                    (active_id, "BOOKED", "UNPAID", Decimal("24000.00")),
                    (cancelled_id, "CANCELLED", "PAID", Decimal("12000.00")),
                ]
                cur.execute(
                    "SELECT showtime_id, seat_id FROM booking_seats WHERE booking_id = %s ORDER BY seat_id",
                    (active_id,),
                )
                assert cur.fetchall() == [(showtime_id, seats[0]), (showtime_id, seats[1])]
                cur.execute("SELECT count(*) FROM booking_seats WHERE booking_id = %s", (cancelled_id,))
                assert cur.fetchone()[0] == 0
        finally:
            conn.close()
    finally:
        db.drop()


def test_migration_0003_aborts_with_23505_on_historical_duplicate_seats(postgres_settings):
    db = _create_db(postgres_settings, (M0001, disposable_db.SEED_PATH))
    try:
        conn = db.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT showtime_id, room_id FROM showtimes "
                    "WHERE starts_at > now() + interval '1 day' ORDER BY showtime_id LIMIT 1"
                )
                showtime_id, room_id = cur.fetchone()
                cur.execute("SELECT seat_id FROM seats WHERE room_id = %s ORDER BY seat_id LIMIT 1", (room_id,))
                seat_id = cur.fetchone()[0]
                cur.execute("SELECT user_id FROM users WHERE role = 'CUSTOMER' ORDER BY user_id LIMIT 2")
                u1, u2 = [r[0] for r in cur.fetchall()]

                cur.execute("SELECT create_booking(%s, %s, %s)", (u1, showtime_id, [seat_id]))
            conn.commit()
            with conn.cursor() as cur:
                # Simulate a historical duplicate allocation before 0003 existed
                cur.execute("ALTER TABLE booking_seats DISABLE TRIGGER trg_booking_seats_validate")
                cur.execute(
                    "INSERT INTO bookings(user_id, showtime_id, total_amount) VALUES (%s, %s, 12000.00) RETURNING booking_id",
                    (u2, showtime_id),
                )
                dup_booking_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO booking_seats(booking_id, seat_id, price_at_booking) VALUES (%s, %s, 12000.00)",
                    (dup_booking_id, seat_id),
                )
            conn.commit()
            with conn.cursor() as cur:
                cur.execute("ALTER TABLE booking_seats ENABLE TRIGGER trg_booking_seats_validate")
            conn.commit()

            with pytest.raises(psycopg2.Error) as excinfo:
                with conn.cursor() as cur:
                    cur.execute(M0003.read_text(encoding="utf-8"))
            assert excinfo.value.pgcode == "23505"
            conn.rollback()

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT numeric_precision FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='bookings' AND column_name='total_amount'"
                )
                assert cur.fetchone()[0] == 10
        finally:
            conn.close()
    finally:
        db.drop()


def test_migration_0004_aborts_with_23514_on_non_finite_money(postgres_settings):
    db = _create_db(postgres_settings, (M0001, M0003, disposable_db.SEED_PATH))
    try:
        conn = db.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE showtimes SET ticket_price = 'NaN'::numeric "
                    "WHERE showtime_id = (SELECT min(showtime_id) FROM showtimes)"
                )
            conn.commit()

            with pytest.raises(psycopg2.Error) as excinfo:
                with conn.cursor() as cur:
                    cur.execute(M0004.read_text(encoding="utf-8"))
            assert excinfo.value.pgcode == "23514"
            conn.rollback()

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM pg_constraint "
                    "WHERE conname = 'showtimes_ticket_price_finite'"
                )
                assert cur.fetchone()[0] == 0
        finally:
            conn.close()
    finally:
        db.drop()


def test_lock_timeout_rolls_back_and_returns_safe_json_error(cinema_template_db):
    with disposable_db.clone_database(cinema_template_db) as clone:
        app = create_app("testing", clone.app_config())
        blocker = clone.connect()
        try:
            with blocker.cursor() as cur:
                cur.execute(
                    "SELECT showtime_id, room_id FROM showtimes "
                    "WHERE starts_at > now() + interval '1 day' ORDER BY showtime_id LIMIT 1"
                )
                showtime_id, room_id = cur.fetchone()
                cur.execute("SELECT seat_id FROM seats WHERE room_id = %s ORDER BY seat_id LIMIT 1", (room_id,))
                seat_id = cur.fetchone()[0]
                cur.execute("SELECT user_id FROM users WHERE role = 'CUSTOMER' ORDER BY user_id LIMIT 1")
                user_id = cur.fetchone()[0]
                # Hold FOR UPDATE lock on the screening row so a second session hits lock_timeout
                cur.execute("SELECT 1 FROM showtimes WHERE showtime_id = %s FOR UPDATE", (showtime_id,))

            @app.post("/_test-lock-timeout")
            def trigger_timeout():
                with transaction() as cur:
                    cur.execute("SET LOCAL lock_timeout = '100ms'")
                    cur.execute("SELECT create_booking(%s, %s, %s)", (user_id, showtime_id, [seat_id]))
                return {"ok": True}

            resp = app.test_client().post("/_test-lock-timeout")
            assert resp.status_code == 503
            assert resp.get_json() == {
                "error": {
                    "code": "database_unavailable",
                    "message": "The service is temporarily unavailable. Please try again later.",
                }
            }
            assert "55P03" not in resp.get_data(as_text=True)
            assert "lock" not in resp.get_data(as_text=True).lower()
        finally:
            blocker.rollback()
            blocker.close()

        verify_conn = clone.connect()
        try:
            with verify_conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM bookings")
                assert cur.fetchone()[0] == 0
        finally:
            verify_conn.close()
