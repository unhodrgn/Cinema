--
-- PostgreSQL database dump
--

\restrict ehAKKosbq0B5g0CqyXpM0ABb3ruIZfMNYnHicfUQDCslTry2YcgChWxxNvS7P1G

-- Dumped from database version 18.7 (Debian 18.7-1.pgdg13+2)
-- Dumped by pg_dump version 18.7 (Debian 18.7-1.pgdg13+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: btree_gist; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public;


--
-- Name: EXTENSION btree_gist; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION btree_gist IS 'support for indexing common datatypes in GiST';


--
-- Name: booking_check_consistency(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.booking_check_consistency() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE v_status text; v_total numeric; v_cnt integer; v_sum numeric;
BEGIN
 SELECT status, total_amount INTO v_status, v_total FROM bookings WHERE booking_id = NEW.booking_id;
 IF v_status IS NULL THEN RETURN NULL; END IF;
 SELECT count(*), COALESCE(sum(price_at_booking), 0) INTO v_cnt, v_sum
   FROM booking_seats WHERE booking_id = NEW.booking_id;
 IF v_status = 'BOOKED' THEN
   IF v_cnt = 0 THEN
     RAISE EXCEPTION 'A BOOKED booking must contain at least one seat' USING ERRCODE = 'UC010';
   END IF;
   IF v_sum <> v_total THEN
     RAISE EXCEPTION 'total_amount (%) must equal the sum of seat price snapshots (%)', v_total, v_sum
       USING ERRCODE = 'UC009';
   END IF;
 ELSIF v_cnt <> 0 THEN
   RAISE EXCEPTION 'A % booking must not keep seat rows', v_status USING ERRCODE = 'UC007';
 END IF;
 RETURN NULL;
END $$;


--
-- Name: booking_seats_protect_delete(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.booking_seats_protect_delete() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
 IF EXISTS (SELECT 1 FROM bookings WHERE booking_id = OLD.booking_id AND status = 'BOOKED') THEN
   RAISE EXCEPTION 'Cancel or expire the booking before releasing its seats' USING ERRCODE = 'UC007';
 END IF;
 RETURN OLD;
END $$;


--
-- Name: booking_seats_validate(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.booking_seats_validate() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
 v_showtime bigint; v_status text; v_room bigint; v_start timestamptz;
 v_price numeric(10,2); v_seat_room bigint;
BEGIN
 IF TG_OP = 'UPDATE' THEN
   RAISE EXCEPTION 'Seat allocations are immutable' USING ERRCODE = 'UC007';
 END IF;
 -- Share-lock the parent so a concurrent state change cannot leave terminal rows allocated.
 SELECT showtime_id, status INTO v_showtime, v_status
   FROM bookings WHERE booking_id = NEW.booking_id FOR SHARE;
 IF v_status IS DISTINCT FROM 'BOOKED' THEN
   RAISE EXCEPTION 'Booking is not BOOKED' USING ERRCODE = 'UC007';
 END IF;
 IF NEW.showtime_id IS NOT NULL AND NEW.showtime_id <> v_showtime THEN
   RAISE EXCEPTION 'Seat allocation must use its booking showtime' USING ERRCODE = '23503';
 END IF;
 NEW.showtime_id := v_showtime;
 SELECT room_id, starts_at, ticket_price INTO v_room, v_start, v_price
   FROM showtimes WHERE showtime_id = v_showtime FOR UPDATE;
 IF v_start <= clock_timestamp() THEN
   RAISE EXCEPTION 'Showtime has already started' USING ERRCODE = 'UC004';
 END IF;
 SELECT room_id INTO v_seat_room FROM seats WHERE seat_id = NEW.seat_id;
 IF v_seat_room IS NULL THEN
   RAISE EXCEPTION 'Seat does not exist' USING ERRCODE = '23503';
 END IF;
 IF v_room IS DISTINCT FROM v_seat_room THEN
   RAISE EXCEPTION 'Seat belongs to another room' USING ERRCODE = 'UC003';
 END IF;
 IF NEW.price_at_booking IS NULL THEN
   NEW.price_at_booking := v_price;                         -- snapshot defaults to the screening price
 ELSIF NEW.price_at_booking <> v_price THEN
   RAISE EXCEPTION 'Price snapshot must equal the screening ticket price' USING ERRCODE = 'UC009';
 END IF;
 -- Fast rejection for visible allocations; the unique index is authoritative.
 IF EXISTS (
   SELECT 1 FROM booking_seats
   WHERE showtime_id = v_showtime AND seat_id = NEW.seat_id
 ) THEN
   RAISE EXCEPTION 'Seat already reserved for this showtime' USING ERRCODE = 'UC002';
 END IF;
 RETURN NEW;
END $$;


--
-- Name: bookings_release_seats(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.bookings_release_seats() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
 IF OLD.status = 'BOOKED' AND NEW.status IN ('CANCELLED','EXPIRED') THEN
   DELETE FROM booking_seats WHERE booking_id = NEW.booking_id;
 END IF;
 RETURN NULL;
END $$;


--
-- Name: bookings_validate(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.bookings_validate() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
 v_now   timestamptz := clock_timestamp();
 v_role  text;
 v_start timestamptz;
BEGIN
 IF TG_OP = 'INSERT' THEN
   SELECT role INTO v_role FROM users WHERE user_id = NEW.user_id;
   IF v_role IS NULL THEN
     RAISE EXCEPTION 'User does not exist' USING ERRCODE = '23503';
   END IF;
   IF v_role IS DISTINCT FROM 'CUSTOMER' THEN
     RAISE EXCEPTION 'Only customers can book' USING ERRCODE = 'UC008';
   END IF;
   SELECT starts_at INTO v_start FROM showtimes WHERE showtime_id = NEW.showtime_id;
   IF v_start <= v_now THEN
     RAISE EXCEPTION 'Showtime has already started' USING ERRCODE = 'UC004';
   END IF;
   IF NEW.status <> 'BOOKED' OR NEW.payment_status <> 'UNPAID'
      OR NEW.paid_at IS NOT NULL OR NEW.cancelled_at IS NOT NULL THEN
     RAISE EXCEPTION 'A new booking must be BOOKED and UNPAID' USING ERRCODE = 'UC007';
   END IF;
   NEW.booked_at  := v_now;
   NEW.expires_at := v_now + interval '10 minutes';        -- D3
   RETURN NEW;
 END IF;

 -- UPDATE
 IF NEW.booking_id <> OLD.booking_id OR NEW.user_id <> OLD.user_id
    OR NEW.showtime_id <> OLD.showtime_id OR NEW.booked_at <> OLD.booked_at
    OR NEW.expires_at <> OLD.expires_at OR NEW.total_amount <> OLD.total_amount THEN
   RAISE EXCEPTION 'Booking identity, timestamps and total_amount cannot be changed' USING ERRCODE = 'UC007';
 END IF;

 IF NEW.status = OLD.status AND NEW.payment_status = OLD.payment_status THEN
   IF NEW.paid_at IS DISTINCT FROM OLD.paid_at OR NEW.cancelled_at IS DISTINCT FROM OLD.cancelled_at THEN
     RAISE EXCEPTION 'paid_at / cancelled_at cannot be edited directly' USING ERRCODE = 'UC007';
   END IF;
   RETURN NEW;                                             -- no state change
 END IF;

 IF OLD.status <> 'BOOKED' THEN
   RAISE EXCEPTION 'Booking is % and can no longer change', OLD.status USING ERRCODE = 'UC007';
 END IF;

 IF NEW.status = 'BOOKED' THEN                             -- payment
   IF OLD.payment_status = 'UNPAID' AND NEW.payment_status = 'PAID' THEN
     IF v_now >= OLD.expires_at THEN
       RAISE EXCEPTION 'Payment window has elapsed' USING ERRCODE = 'UC006';
     END IF;
     NEW.paid_at := v_now;
     NEW.cancelled_at := NULL;
     RETURN NEW;
   END IF;
   RAISE EXCEPTION 'Illegal payment status transition % -> %', OLD.payment_status, NEW.payment_status
     USING ERRCODE = 'UC007';

 ELSIF NEW.status = 'CANCELLED' THEN                       -- D1
   IF NEW.payment_status <> OLD.payment_status THEN
     RAISE EXCEPTION 'Payment status cannot change while cancelling' USING ERRCODE = 'UC007';
   END IF;
   IF OLD.payment_status = 'UNPAID' AND v_now >= OLD.expires_at THEN
     RAISE EXCEPTION 'Payment window has elapsed; the booking must expire, not be cancelled'
       USING ERRCODE = 'UC006';
   END IF;
   SELECT starts_at INTO v_start FROM showtimes WHERE showtime_id = OLD.showtime_id;
   IF v_start <= v_now THEN
     RAISE EXCEPTION 'Cannot cancel after showtime starts' USING ERRCODE = 'UC005';
   END IF;
   NEW.cancelled_at := v_now;
   NEW.paid_at := OLD.paid_at;
   RETURN NEW;

 ELSIF NEW.status = 'EXPIRED' THEN                         -- D3: deliberately NOT blocked by screening start
   IF OLD.payment_status <> 'UNPAID' OR NEW.payment_status <> 'UNPAID' THEN
     RAISE EXCEPTION 'Only unpaid bookings can expire' USING ERRCODE = 'UC007';
   END IF;
   IF v_now < OLD.expires_at THEN
     RAISE EXCEPTION 'Payment window has not elapsed' USING ERRCODE = 'UC006';
   END IF;
   NEW.cancelled_at := NULL;
   NEW.paid_at := NULL;
   RETURN NEW;
 END IF;
 RETURN NEW;
END $$;


--
-- Name: bookings_version_first_showtime_reference(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.bookings_version_first_showtime_reference() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
 UPDATE showtimes s SET ticket_price = s.ticket_price
 WHERE s.showtime_id = NEW.showtime_id
   AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.showtime_id = s.showtime_id);
 RETURN NEW;
END $$;


--
-- Name: cancel_booking(bigint, bigint, timestamp with time zone); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cancel_booking(p_booking_id bigint, p_user_id bigint, p_as_of timestamp with time zone DEFAULT clock_timestamp()) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE b bookings%ROWTYPE;
BEGIN
 SELECT * INTO b FROM bookings WHERE booking_id = p_booking_id AND user_id = p_user_id FOR UPDATE;
 IF NOT FOUND THEN
   RAISE EXCEPTION 'Booking not found' USING ERRCODE = 'UC011';
 END IF;
 IF b.status <> 'BOOKED' THEN
   RAISE EXCEPTION 'Booking is % and cannot be cancelled', b.status USING ERRCODE = 'UC006';
 END IF;
 IF b.payment_status = 'UNPAID' AND p_as_of >= b.expires_at THEN
   UPDATE bookings SET status = 'EXPIRED' WHERE booking_id = b.booking_id;
   RETURN 'EXPIRED';
 END IF;
 UPDATE bookings SET status = 'CANCELLED' WHERE booking_id = b.booking_id;
 RETURN 'CANCELLED';
END $$;


--
-- Name: create_booking(bigint, bigint, bigint[]); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.create_booking(p_user_id bigint, p_showtime_id bigint, p_seat_ids bigint[]) RETURNS bigint
    LANGUAGE plpgsql
    AS $$
DECLARE v_price numeric(10,2); v_id bigint; v_n integer; v_constraint text;
BEGIN
 v_n := COALESCE(cardinality(p_seat_ids), 0);
 IF v_n = 0 THEN
   RAISE EXCEPTION 'At least one seat is required' USING ERRCODE = 'UC010';
 END IF;
 IF (SELECT count(DISTINCT s) FROM unnest(p_seat_ids) AS s) <> v_n THEN
   RAISE EXCEPTION 'Seat list contains duplicates or NULL' USING ERRCODE = 'UC010';
 END IF;
 SELECT ticket_price INTO v_price FROM showtimes WHERE showtime_id = p_showtime_id FOR UPDATE;
 IF NOT FOUND THEN
   RAISE EXCEPTION 'Screening not found' USING ERRCODE = 'UC011';
 END IF;
 PERFORM expire_overdue_bookings();
 INSERT INTO bookings(user_id, showtime_id, total_amount)
 VALUES (p_user_id, p_showtime_id, v_price * v_n)
 RETURNING booking_id INTO v_id;
 BEGIN
   INSERT INTO booking_seats(booking_id, seat_id, price_at_booking)
   SELECT v_id, s, v_price FROM unnest(p_seat_ids) AS s ORDER BY s;
 EXCEPTION WHEN unique_violation THEN
   GET STACKED DIAGNOSTICS v_constraint = CONSTRAINT_NAME;
   IF v_constraint = 'booking_seats_showtime_seat_key' THEN
     RAISE EXCEPTION 'Seat already reserved for this showtime' USING ERRCODE = 'UC002';
   END IF;
   RAISE;
 END;
 RETURN v_id;
END $$;


--
-- Name: expire_overdue_bookings(timestamp with time zone); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.expire_overdue_bookings(p_as_of timestamp with time zone DEFAULT clock_timestamp()) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE v_count integer;
BEGIN
 UPDATE bookings SET status = 'EXPIRED'
 WHERE booking_id IN (
   SELECT booking_id FROM bookings
   WHERE status = 'BOOKED' AND payment_status = 'UNPAID' AND expires_at <= p_as_of
   ORDER BY booking_id
   FOR UPDATE SKIP LOCKED
 );
 GET DIAGNOSTICS v_count = ROW_COUNT;
 RETURN v_count;
END $$;


--
-- Name: pay_booking(bigint, bigint, timestamp with time zone); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.pay_booking(p_booking_id bigint, p_user_id bigint, p_as_of timestamp with time zone DEFAULT clock_timestamp()) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE b bookings%ROWTYPE;
BEGIN
 SELECT * INTO b FROM bookings WHERE booking_id = p_booking_id AND user_id = p_user_id FOR UPDATE;
 IF NOT FOUND THEN
   RAISE EXCEPTION 'Booking not found' USING ERRCODE = 'UC011';
 END IF;
 IF b.status <> 'BOOKED' THEN
   RAISE EXCEPTION 'Booking is % and cannot be paid', b.status USING ERRCODE = 'UC006';
 END IF;
 IF b.payment_status = 'PAID' THEN
   RAISE EXCEPTION 'Booking is already paid' USING ERRCODE = 'UC006';
 END IF;
 IF p_as_of >= b.expires_at THEN
   UPDATE bookings SET status = 'EXPIRED' WHERE booking_id = b.booking_id;
   RETURN 'EXPIRED';
 END IF;
 UPDATE bookings SET payment_status = 'PAID' WHERE booking_id = b.booking_id;
 RETURN 'PAID';
END $$;


--
-- Name: showtimes_default_end_time(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.showtimes_default_end_time() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE v_minutes integer;
BEGIN
 IF NEW.ends_at IS NULL THEN
   SELECT duration_minutes INTO v_minutes FROM movies WHERE movie_id = NEW.movie_id;
   IF v_minutes IS NOT NULL THEN
     NEW.ends_at := NEW.starts_at + v_minutes * interval '1 minute';
   END IF;
 END IF;
 RETURN NEW;
END $$;


--
-- Name: showtimes_protect_booked(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.showtimes_protect_booked() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
 IF (NEW.movie_id, NEW.room_id, NEW.starts_at, NEW.ends_at, NEW.ticket_price)
    IS DISTINCT FROM
    (OLD.movie_id, OLD.room_id, OLD.starts_at, OLD.ends_at, OLD.ticket_price)
    AND EXISTS (SELECT 1 FROM bookings WHERE showtime_id = OLD.showtime_id) THEN
   RAISE EXCEPTION 'Cannot modify a screening that has booking records' USING ERRCODE = 'UC001';
 END IF;
 RETURN NEW;
END $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: booking_seats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.booking_seats (
    booking_seat_id bigint NOT NULL,
    booking_id bigint NOT NULL,
    seat_id bigint NOT NULL,
    price_at_booking numeric(10,2) NOT NULL,
    showtime_id bigint NOT NULL,
    CONSTRAINT booking_seats_price_at_booking_check CHECK ((price_at_booking >= (0)::numeric)),
    CONSTRAINT booking_seats_price_at_booking_finite CHECK ((price_at_booking <> ALL (ARRAY['NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric])))
);


--
-- Name: booking_seats_booking_seat_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.booking_seats ALTER COLUMN booking_seat_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.booking_seats_booking_seat_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: bookings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bookings (
    booking_id bigint NOT NULL,
    user_id bigint NOT NULL,
    showtime_id bigint NOT NULL,
    status character varying(10) DEFAULT 'BOOKED'::character varying NOT NULL,
    payment_status character varying(10) DEFAULT 'UNPAID'::character varying NOT NULL,
    booked_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    total_amount numeric(12,2) NOT NULL,
    paid_at timestamp with time zone,
    cancelled_at timestamp with time zone,
    CONSTRAINT bookings_cancelled_at_matches CHECK ((((status)::text = 'CANCELLED'::text) = (cancelled_at IS NOT NULL))),
    CONSTRAINT bookings_expiry_is_10_minutes CHECK ((expires_at = (booked_at + '00:10:00'::interval))),
    CONSTRAINT bookings_paid_at_matches CHECK ((((payment_status)::text = 'PAID'::text) = (paid_at IS NOT NULL))),
    CONSTRAINT bookings_paid_never_expired CHECK ((NOT (((status)::text = 'EXPIRED'::text) AND ((payment_status)::text = 'PAID'::text)))),
    CONSTRAINT bookings_payment_status_check CHECK (((payment_status)::text = ANY ((ARRAY['UNPAID'::character varying, 'PAID'::character varying])::text[]))),
    CONSTRAINT bookings_status_check CHECK (((status)::text = ANY ((ARRAY['BOOKED'::character varying, 'CANCELLED'::character varying, 'EXPIRED'::character varying])::text[]))),
    CONSTRAINT bookings_total_amount_check CHECK ((total_amount >= (0)::numeric)),
    CONSTRAINT bookings_total_amount_finite CHECK ((total_amount <> ALL (ARRAY['NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric])))
);


--
-- Name: bookings_booking_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.bookings ALTER COLUMN booking_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.bookings_booking_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: movies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.movies (
    movie_id bigint NOT NULL,
    title character varying(200) NOT NULL,
    genre character varying(100),
    duration_minutes integer NOT NULL,
    rating character varying(50),
    synopsis text,
    release_date date,
    poster_url character varying(255),
    CONSTRAINT movies_duration_minutes_check CHECK (((duration_minutes >= 1) AND (duration_minutes <= 300))),
    CONSTRAINT movies_poster_url_check CHECK (((poster_url)::text ~ '^/images/posters/[A-Za-z0-9][A-Za-z0-9._-]*\.(jpg|png)$'::text))
);


--
-- Name: movies_movie_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.movies ALTER COLUMN movie_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.movies_movie_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: seats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.seats (
    seat_id bigint NOT NULL,
    room_id bigint NOT NULL,
    seat_row character(1) NOT NULL,
    seat_number smallint NOT NULL,
    CONSTRAINT seats_seat_number_check CHECK (((seat_number >= 1) AND (seat_number <= 10))),
    CONSTRAINT seats_seat_row_check CHECK ((seat_row = ANY (ARRAY['A'::bpchar, 'B'::bpchar, 'C'::bpchar, 'D'::bpchar, 'E'::bpchar])))
);


--
-- Name: seats_seat_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.seats ALTER COLUMN seat_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.seats_seat_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: showtimes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.showtimes (
    showtime_id bigint NOT NULL,
    movie_id bigint NOT NULL,
    room_id bigint NOT NULL,
    starts_at timestamp with time zone NOT NULL,
    ends_at timestamp with time zone NOT NULL,
    ticket_price numeric(10,2) NOT NULL,
    CONSTRAINT showtimes_end_after_start CHECK ((ends_at > starts_at)),
    CONSTRAINT showtimes_ticket_price_check CHECK ((ticket_price >= (0)::numeric)),
    CONSTRAINT showtimes_ticket_price_finite CHECK ((ticket_price <> ALL (ARRAY['NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric])))
);


--
-- Name: showtimes_showtime_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.showtimes ALTER COLUMN showtime_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.showtimes_showtime_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: theater_rooms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.theater_rooms (
    room_id bigint NOT NULL,
    room_name character varying(60) NOT NULL
);


--
-- Name: theater_rooms_room_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.theater_rooms ALTER COLUMN room_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.theater_rooms_room_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    user_id bigint NOT NULL,
    username character varying(60) NOT NULL,
    password_hash text NOT NULL,
    role character varying(10) DEFAULT 'CUSTOMER'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT users_role_check CHECK (((role)::text = ANY ((ARRAY['CUSTOMER'::character varying, 'ADMIN'::character varying])::text[])))
);


--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.users ALTER COLUMN user_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.users_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Data for Name: booking_seats; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.booking_seats (booking_seat_id, booking_id, seat_id, price_at_booking, showtime_id) FROM stdin;
\.


--
-- Data for Name: bookings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.bookings (booking_id, user_id, showtime_id, status, payment_status, booked_at, expires_at, total_amount, paid_at, cancelled_at) FROM stdin;
\.


--
-- Data for Name: movies; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.movies (movie_id, title, genre, duration_minutes, rating, synopsis, release_date, poster_url) FROM stdin;
1	Jujutsu Kaisen 0	Animation	105	15	Yuta Okkotsu, haunted by the cursed spirit of his childhood friend, is taken in by Tokyo Jujutsu High.	2022-02-17	/images/posters/jjk-0.jpg
2	Jujutsu Kaisen: Hidden Inventory / Premature Death	Animation	110	15	Gojo and Geto take on a mission to guard the Star Plasma Vessel, a job that will change both of them.	2025-10-16	/images/posters/jjk-hidden-inventory.jpg
3	Jujutsu Kaisen: Execution	Animation	87	15	The Shibuya Incident is retold and followed by a first look at the Culling Game.	2025-12-03	/images/posters/jjk-execution.jpg
4	20th Century Girl	Romance	119	12	In 1999, a teenager promises to collect every detail of her best friend's first crush.	2022-10-06	/images/posters/20th-century-girl.jpg
5	Exhuma	Horror	134	15	Shamans, a feng shui master and an undertaker move a wealthy family's cursed ancestral grave.	2024-02-22	/images/posters/exhuma.jpg
6	Godzilla x Kong: The New Empire	Action	115	12	Godzilla and Kong must join forces against a hidden threat buried deep in the Hollow Earth.	2024-03-27	/images/posters/godzilla-x-kong.jpg
\.


--
-- Data for Name: seats; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.seats (seat_id, room_id, seat_row, seat_number) FROM stdin;
1	1	A	1
2	1	A	2
3	1	A	3
4	1	A	4
5	1	A	5
6	1	A	6
7	1	A	7
8	1	A	8
9	1	A	9
10	1	A	10
11	1	B	1
12	1	B	2
13	1	B	3
14	1	B	4
15	1	B	5
16	1	B	6
17	1	B	7
18	1	B	8
19	1	B	9
20	1	B	10
21	1	C	1
22	1	C	2
23	1	C	3
24	1	C	4
25	1	C	5
26	1	C	6
27	1	C	7
28	1	C	8
29	1	C	9
30	1	C	10
31	1	D	1
32	1	D	2
33	1	D	3
34	1	D	4
35	1	D	5
36	1	D	6
37	1	D	7
38	1	D	8
39	1	D	9
40	1	D	10
41	1	E	1
42	1	E	2
43	1	E	3
44	1	E	4
45	1	E	5
46	1	E	6
47	1	E	7
48	1	E	8
49	1	E	9
50	1	E	10
51	2	A	1
52	2	A	2
53	2	A	3
54	2	A	4
55	2	A	5
56	2	A	6
57	2	A	7
58	2	A	8
59	2	A	9
60	2	A	10
61	2	B	1
62	2	B	2
63	2	B	3
64	2	B	4
65	2	B	5
66	2	B	6
67	2	B	7
68	2	B	8
69	2	B	9
70	2	B	10
71	2	C	1
72	2	C	2
73	2	C	3
74	2	C	4
75	2	C	5
76	2	C	6
77	2	C	7
78	2	C	8
79	2	C	9
80	2	C	10
81	2	D	1
82	2	D	2
83	2	D	3
84	2	D	4
85	2	D	5
86	2	D	6
87	2	D	7
88	2	D	8
89	2	D	9
90	2	D	10
91	2	E	1
92	2	E	2
93	2	E	3
94	2	E	4
95	2	E	5
96	2	E	6
97	2	E	7
98	2	E	8
99	2	E	9
100	2	E	10
101	3	A	1
102	3	A	2
103	3	A	3
104	3	A	4
105	3	A	5
106	3	A	6
107	3	A	7
108	3	A	8
109	3	A	9
110	3	A	10
111	3	B	1
112	3	B	2
113	3	B	3
114	3	B	4
115	3	B	5
116	3	B	6
117	3	B	7
118	3	B	8
119	3	B	9
120	3	B	10
121	3	C	1
122	3	C	2
123	3	C	3
124	3	C	4
125	3	C	5
126	3	C	6
127	3	C	7
128	3	C	8
129	3	C	9
130	3	C	10
131	3	D	1
132	3	D	2
133	3	D	3
134	3	D	4
135	3	D	5
136	3	D	6
137	3	D	7
138	3	D	8
139	3	D	9
140	3	D	10
141	3	E	1
142	3	E	2
143	3	E	3
144	3	E	4
145	3	E	5
146	3	E	6
147	3	E	7
148	3	E	8
149	3	E	9
150	3	E	10
151	4	A	1
152	4	A	2
153	4	A	3
154	4	A	4
155	4	A	5
156	4	A	6
157	4	A	7
158	4	A	8
159	4	A	9
160	4	A	10
161	4	B	1
162	4	B	2
163	4	B	3
164	4	B	4
165	4	B	5
166	4	B	6
167	4	B	7
168	4	B	8
169	4	B	9
170	4	B	10
171	4	C	1
172	4	C	2
173	4	C	3
174	4	C	4
175	4	C	5
176	4	C	6
177	4	C	7
178	4	C	8
179	4	C	9
180	4	C	10
181	4	D	1
182	4	D	2
183	4	D	3
184	4	D	4
185	4	D	5
186	4	D	6
187	4	D	7
188	4	D	8
189	4	D	9
190	4	D	10
191	4	E	1
192	4	E	2
193	4	E	3
194	4	E	4
195	4	E	5
196	4	E	6
197	4	E	7
198	4	E	8
199	4	E	9
200	4	E	10
201	5	A	1
202	5	A	2
203	5	A	3
204	5	A	4
205	5	A	5
206	5	A	6
207	5	A	7
208	5	A	8
209	5	A	9
210	5	A	10
211	5	B	1
212	5	B	2
213	5	B	3
214	5	B	4
215	5	B	5
216	5	B	6
217	5	B	7
218	5	B	8
219	5	B	9
220	5	B	10
221	5	C	1
222	5	C	2
223	5	C	3
224	5	C	4
225	5	C	5
226	5	C	6
227	5	C	7
228	5	C	8
229	5	C	9
230	5	C	10
231	5	D	1
232	5	D	2
233	5	D	3
234	5	D	4
235	5	D	5
236	5	D	6
237	5	D	7
238	5	D	8
239	5	D	9
240	5	D	10
241	5	E	1
242	5	E	2
243	5	E	3
244	5	E	4
245	5	E	5
246	5	E	6
247	5	E	7
248	5	E	8
249	5	E	9
250	5	E	10
\.


--
-- Data for Name: showtimes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.showtimes (showtime_id, movie_id, room_id, starts_at, ends_at, ticket_price) FROM stdin;
1	1	1	2026-11-26 01:00:00+00	2026-11-26 02:45:00+00	12000.00
2	2	1	2026-11-26 04:00:00+00	2026-11-26 05:50:00+00	12000.00
3	3	1	2026-11-26 07:00:00+00	2026-11-26 08:27:00+00	12000.00
4	4	1	2026-11-26 10:00:00+00	2026-11-26 11:59:00+00	12000.00
5	2	2	2026-11-26 01:00:00+00	2026-11-26 02:50:00+00	12000.00
6	3	2	2026-11-26 04:00:00+00	2026-11-26 05:27:00+00	12000.00
7	4	2	2026-11-26 07:00:00+00	2026-11-26 08:59:00+00	12000.00
8	5	2	2026-11-26 10:00:00+00	2026-11-26 12:14:00+00	12000.00
9	3	3	2026-11-26 01:00:00+00	2026-11-26 02:27:00+00	12000.00
10	4	3	2026-11-26 04:00:00+00	2026-11-26 05:59:00+00	12000.00
11	5	3	2026-11-26 07:00:00+00	2026-11-26 09:14:00+00	12000.00
12	6	3	2026-11-26 10:00:00+00	2026-11-26 11:55:00+00	12000.00
13	4	4	2026-11-26 01:00:00+00	2026-11-26 02:59:00+00	12000.00
14	5	4	2026-11-26 04:00:00+00	2026-11-26 06:14:00+00	12000.00
15	6	4	2026-11-26 07:00:00+00	2026-11-26 08:55:00+00	12000.00
16	1	4	2026-11-26 10:00:00+00	2026-11-26 11:45:00+00	12000.00
17	5	5	2026-11-26 01:00:00+00	2026-11-26 03:14:00+00	12000.00
18	6	5	2026-11-26 04:00:00+00	2026-11-26 05:55:00+00	12000.00
19	1	5	2026-11-26 07:00:00+00	2026-11-26 08:45:00+00	12000.00
20	2	5	2026-11-26 10:00:00+00	2026-11-26 11:50:00+00	12000.00
21	1	1	2026-11-27 01:00:00+00	2026-11-27 02:45:00+00	12000.00
22	2	1	2026-11-27 04:00:00+00	2026-11-27 05:50:00+00	12000.00
23	3	1	2026-11-27 07:00:00+00	2026-11-27 08:27:00+00	12000.00
24	4	1	2026-11-27 10:00:00+00	2026-11-27 11:59:00+00	12000.00
25	2	2	2026-11-27 01:00:00+00	2026-11-27 02:50:00+00	12000.00
26	3	2	2026-11-27 04:00:00+00	2026-11-27 05:27:00+00	12000.00
27	4	2	2026-11-27 07:00:00+00	2026-11-27 08:59:00+00	12000.00
28	5	2	2026-11-27 10:00:00+00	2026-11-27 12:14:00+00	12000.00
29	3	3	2026-11-27 01:00:00+00	2026-11-27 02:27:00+00	12000.00
30	4	3	2026-11-27 04:00:00+00	2026-11-27 05:59:00+00	12000.00
31	5	3	2026-11-27 07:00:00+00	2026-11-27 09:14:00+00	12000.00
32	6	3	2026-11-27 10:00:00+00	2026-11-27 11:55:00+00	12000.00
33	4	4	2026-11-27 01:00:00+00	2026-11-27 02:59:00+00	12000.00
34	5	4	2026-11-27 04:00:00+00	2026-11-27 06:14:00+00	12000.00
35	6	4	2026-11-27 07:00:00+00	2026-11-27 08:55:00+00	12000.00
36	1	4	2026-11-27 10:00:00+00	2026-11-27 11:45:00+00	12000.00
37	5	5	2026-11-27 01:00:00+00	2026-11-27 03:14:00+00	12000.00
38	6	5	2026-11-27 04:00:00+00	2026-11-27 05:55:00+00	12000.00
39	1	5	2026-11-27 07:00:00+00	2026-11-27 08:45:00+00	12000.00
40	2	5	2026-11-27 10:00:00+00	2026-11-27 11:50:00+00	12000.00
41	1	1	2026-11-28 01:00:00+00	2026-11-28 02:45:00+00	12000.00
42	2	1	2026-11-28 04:00:00+00	2026-11-28 05:50:00+00	12000.00
43	3	1	2026-11-28 07:00:00+00	2026-11-28 08:27:00+00	12000.00
44	4	1	2026-11-28 10:00:00+00	2026-11-28 11:59:00+00	12000.00
45	2	2	2026-11-28 01:00:00+00	2026-11-28 02:50:00+00	12000.00
46	3	2	2026-11-28 04:00:00+00	2026-11-28 05:27:00+00	12000.00
47	4	2	2026-11-28 07:00:00+00	2026-11-28 08:59:00+00	12000.00
48	5	2	2026-11-28 10:00:00+00	2026-11-28 12:14:00+00	12000.00
49	3	3	2026-11-28 01:00:00+00	2026-11-28 02:27:00+00	12000.00
50	4	3	2026-11-28 04:00:00+00	2026-11-28 05:59:00+00	12000.00
51	5	3	2026-11-28 07:00:00+00	2026-11-28 09:14:00+00	12000.00
52	6	3	2026-11-28 10:00:00+00	2026-11-28 11:55:00+00	12000.00
53	4	4	2026-11-28 01:00:00+00	2026-11-28 02:59:00+00	12000.00
54	5	4	2026-11-28 04:00:00+00	2026-11-28 06:14:00+00	12000.00
55	6	4	2026-11-28 07:00:00+00	2026-11-28 08:55:00+00	12000.00
56	1	4	2026-11-28 10:00:00+00	2026-11-28 11:45:00+00	12000.00
57	5	5	2026-11-28 01:00:00+00	2026-11-28 03:14:00+00	12000.00
58	6	5	2026-11-28 04:00:00+00	2026-11-28 05:55:00+00	12000.00
59	1	5	2026-11-28 07:00:00+00	2026-11-28 08:45:00+00	12000.00
60	2	5	2026-11-28 10:00:00+00	2026-11-28 11:50:00+00	12000.00
61	1	1	2026-11-29 01:00:00+00	2026-11-29 02:45:00+00	12000.00
62	2	1	2026-11-29 04:00:00+00	2026-11-29 05:50:00+00	12000.00
63	3	1	2026-11-29 07:00:00+00	2026-11-29 08:27:00+00	12000.00
64	4	1	2026-11-29 10:00:00+00	2026-11-29 11:59:00+00	12000.00
65	2	2	2026-11-29 01:00:00+00	2026-11-29 02:50:00+00	12000.00
66	3	2	2026-11-29 04:00:00+00	2026-11-29 05:27:00+00	12000.00
67	4	2	2026-11-29 07:00:00+00	2026-11-29 08:59:00+00	12000.00
68	5	2	2026-11-29 10:00:00+00	2026-11-29 12:14:00+00	12000.00
69	3	3	2026-11-29 01:00:00+00	2026-11-29 02:27:00+00	12000.00
70	4	3	2026-11-29 04:00:00+00	2026-11-29 05:59:00+00	12000.00
71	5	3	2026-11-29 07:00:00+00	2026-11-29 09:14:00+00	12000.00
72	6	3	2026-11-29 10:00:00+00	2026-11-29 11:55:00+00	12000.00
73	4	4	2026-11-29 01:00:00+00	2026-11-29 02:59:00+00	12000.00
74	5	4	2026-11-29 04:00:00+00	2026-11-29 06:14:00+00	12000.00
75	6	4	2026-11-29 07:00:00+00	2026-11-29 08:55:00+00	12000.00
76	1	4	2026-11-29 10:00:00+00	2026-11-29 11:45:00+00	12000.00
77	5	5	2026-11-29 01:00:00+00	2026-11-29 03:14:00+00	12000.00
78	6	5	2026-11-29 04:00:00+00	2026-11-29 05:55:00+00	12000.00
79	1	5	2026-11-29 07:00:00+00	2026-11-29 08:45:00+00	12000.00
80	2	5	2026-11-29 10:00:00+00	2026-11-29 11:50:00+00	12000.00
81	1	1	2026-11-30 01:00:00+00	2026-11-30 02:45:00+00	12000.00
82	2	1	2026-11-30 04:00:00+00	2026-11-30 05:50:00+00	12000.00
83	3	1	2026-11-30 07:00:00+00	2026-11-30 08:27:00+00	12000.00
84	4	1	2026-11-30 10:00:00+00	2026-11-30 11:59:00+00	12000.00
85	2	2	2026-11-30 01:00:00+00	2026-11-30 02:50:00+00	12000.00
86	3	2	2026-11-30 04:00:00+00	2026-11-30 05:27:00+00	12000.00
87	4	2	2026-11-30 07:00:00+00	2026-11-30 08:59:00+00	12000.00
88	5	2	2026-11-30 10:00:00+00	2026-11-30 12:14:00+00	12000.00
89	3	3	2026-11-30 01:00:00+00	2026-11-30 02:27:00+00	12000.00
90	4	3	2026-11-30 04:00:00+00	2026-11-30 05:59:00+00	12000.00
91	5	3	2026-11-30 07:00:00+00	2026-11-30 09:14:00+00	12000.00
92	6	3	2026-11-30 10:00:00+00	2026-11-30 11:55:00+00	12000.00
93	4	4	2026-11-30 01:00:00+00	2026-11-30 02:59:00+00	12000.00
94	5	4	2026-11-30 04:00:00+00	2026-11-30 06:14:00+00	12000.00
95	6	4	2026-11-30 07:00:00+00	2026-11-30 08:55:00+00	12000.00
96	1	4	2026-11-30 10:00:00+00	2026-11-30 11:45:00+00	12000.00
97	5	5	2026-11-30 01:00:00+00	2026-11-30 03:14:00+00	12000.00
98	6	5	2026-11-30 04:00:00+00	2026-11-30 05:55:00+00	12000.00
99	1	5	2026-11-30 07:00:00+00	2026-11-30 08:45:00+00	12000.00
100	2	5	2026-11-30 10:00:00+00	2026-11-30 11:50:00+00	12000.00
101	1	1	2026-12-01 01:00:00+00	2026-12-01 02:45:00+00	12000.00
102	2	1	2026-12-01 04:00:00+00	2026-12-01 05:50:00+00	12000.00
103	3	1	2026-12-01 07:00:00+00	2026-12-01 08:27:00+00	12000.00
104	4	1	2026-12-01 10:00:00+00	2026-12-01 11:59:00+00	12000.00
105	2	2	2026-12-01 01:00:00+00	2026-12-01 02:50:00+00	12000.00
106	3	2	2026-12-01 04:00:00+00	2026-12-01 05:27:00+00	12000.00
107	4	2	2026-12-01 07:00:00+00	2026-12-01 08:59:00+00	12000.00
108	5	2	2026-12-01 10:00:00+00	2026-12-01 12:14:00+00	12000.00
109	3	3	2026-12-01 01:00:00+00	2026-12-01 02:27:00+00	12000.00
110	4	3	2026-12-01 04:00:00+00	2026-12-01 05:59:00+00	12000.00
111	5	3	2026-12-01 07:00:00+00	2026-12-01 09:14:00+00	12000.00
112	6	3	2026-12-01 10:00:00+00	2026-12-01 11:55:00+00	12000.00
113	4	4	2026-12-01 01:00:00+00	2026-12-01 02:59:00+00	12000.00
114	5	4	2026-12-01 04:00:00+00	2026-12-01 06:14:00+00	12000.00
115	6	4	2026-12-01 07:00:00+00	2026-12-01 08:55:00+00	12000.00
116	1	4	2026-12-01 10:00:00+00	2026-12-01 11:45:00+00	12000.00
117	5	5	2026-12-01 01:00:00+00	2026-12-01 03:14:00+00	12000.00
118	6	5	2026-12-01 04:00:00+00	2026-12-01 05:55:00+00	12000.00
119	1	5	2026-12-01 07:00:00+00	2026-12-01 08:45:00+00	12000.00
120	2	5	2026-12-01 10:00:00+00	2026-12-01 11:50:00+00	12000.00
121	1	1	2026-12-02 01:00:00+00	2026-12-02 02:45:00+00	12000.00
122	2	1	2026-12-02 04:00:00+00	2026-12-02 05:50:00+00	12000.00
123	3	1	2026-12-02 07:00:00+00	2026-12-02 08:27:00+00	12000.00
124	4	1	2026-12-02 10:00:00+00	2026-12-02 11:59:00+00	12000.00
125	2	2	2026-12-02 01:00:00+00	2026-12-02 02:50:00+00	12000.00
126	3	2	2026-12-02 04:00:00+00	2026-12-02 05:27:00+00	12000.00
127	4	2	2026-12-02 07:00:00+00	2026-12-02 08:59:00+00	12000.00
128	5	2	2026-12-02 10:00:00+00	2026-12-02 12:14:00+00	12000.00
129	3	3	2026-12-02 01:00:00+00	2026-12-02 02:27:00+00	12000.00
130	4	3	2026-12-02 04:00:00+00	2026-12-02 05:59:00+00	12000.00
131	5	3	2026-12-02 07:00:00+00	2026-12-02 09:14:00+00	12000.00
132	6	3	2026-12-02 10:00:00+00	2026-12-02 11:55:00+00	12000.00
133	4	4	2026-12-02 01:00:00+00	2026-12-02 02:59:00+00	12000.00
134	5	4	2026-12-02 04:00:00+00	2026-12-02 06:14:00+00	12000.00
135	6	4	2026-12-02 07:00:00+00	2026-12-02 08:55:00+00	12000.00
136	1	4	2026-12-02 10:00:00+00	2026-12-02 11:45:00+00	12000.00
137	5	5	2026-12-02 01:00:00+00	2026-12-02 03:14:00+00	12000.00
138	6	5	2026-12-02 04:00:00+00	2026-12-02 05:55:00+00	12000.00
139	1	5	2026-12-02 07:00:00+00	2026-12-02 08:45:00+00	12000.00
140	2	5	2026-12-02 10:00:00+00	2026-12-02 11:50:00+00	12000.00
141	1	1	2026-12-03 01:00:00+00	2026-12-03 02:45:00+00	12000.00
142	2	1	2026-12-03 04:00:00+00	2026-12-03 05:50:00+00	12000.00
143	3	1	2026-12-03 07:00:00+00	2026-12-03 08:27:00+00	12000.00
144	4	1	2026-12-03 10:00:00+00	2026-12-03 11:59:00+00	12000.00
145	2	2	2026-12-03 01:00:00+00	2026-12-03 02:50:00+00	12000.00
146	3	2	2026-12-03 04:00:00+00	2026-12-03 05:27:00+00	12000.00
147	4	2	2026-12-03 07:00:00+00	2026-12-03 08:59:00+00	12000.00
148	5	2	2026-12-03 10:00:00+00	2026-12-03 12:14:00+00	12000.00
149	3	3	2026-12-03 01:00:00+00	2026-12-03 02:27:00+00	12000.00
150	4	3	2026-12-03 04:00:00+00	2026-12-03 05:59:00+00	12000.00
151	5	3	2026-12-03 07:00:00+00	2026-12-03 09:14:00+00	12000.00
152	6	3	2026-12-03 10:00:00+00	2026-12-03 11:55:00+00	12000.00
153	4	4	2026-12-03 01:00:00+00	2026-12-03 02:59:00+00	12000.00
154	5	4	2026-12-03 04:00:00+00	2026-12-03 06:14:00+00	12000.00
155	6	4	2026-12-03 07:00:00+00	2026-12-03 08:55:00+00	12000.00
156	1	4	2026-12-03 10:00:00+00	2026-12-03 11:45:00+00	12000.00
157	5	5	2026-12-03 01:00:00+00	2026-12-03 03:14:00+00	12000.00
158	6	5	2026-12-03 04:00:00+00	2026-12-03 05:55:00+00	12000.00
159	1	5	2026-12-03 07:00:00+00	2026-12-03 08:45:00+00	12000.00
160	2	5	2026-12-03 10:00:00+00	2026-12-03 11:50:00+00	12000.00
161	1	1	2026-12-04 01:00:00+00	2026-12-04 02:45:00+00	12000.00
162	2	1	2026-12-04 04:00:00+00	2026-12-04 05:50:00+00	12000.00
163	3	1	2026-12-04 07:00:00+00	2026-12-04 08:27:00+00	12000.00
164	4	1	2026-12-04 10:00:00+00	2026-12-04 11:59:00+00	12000.00
165	2	2	2026-12-04 01:00:00+00	2026-12-04 02:50:00+00	12000.00
166	3	2	2026-12-04 04:00:00+00	2026-12-04 05:27:00+00	12000.00
167	4	2	2026-12-04 07:00:00+00	2026-12-04 08:59:00+00	12000.00
168	5	2	2026-12-04 10:00:00+00	2026-12-04 12:14:00+00	12000.00
169	3	3	2026-12-04 01:00:00+00	2026-12-04 02:27:00+00	12000.00
170	4	3	2026-12-04 04:00:00+00	2026-12-04 05:59:00+00	12000.00
171	5	3	2026-12-04 07:00:00+00	2026-12-04 09:14:00+00	12000.00
172	6	3	2026-12-04 10:00:00+00	2026-12-04 11:55:00+00	12000.00
173	4	4	2026-12-04 01:00:00+00	2026-12-04 02:59:00+00	12000.00
174	5	4	2026-12-04 04:00:00+00	2026-12-04 06:14:00+00	12000.00
175	6	4	2026-12-04 07:00:00+00	2026-12-04 08:55:00+00	12000.00
176	1	4	2026-12-04 10:00:00+00	2026-12-04 11:45:00+00	12000.00
177	5	5	2026-12-04 01:00:00+00	2026-12-04 03:14:00+00	12000.00
178	6	5	2026-12-04 04:00:00+00	2026-12-04 05:55:00+00	12000.00
179	1	5	2026-12-04 07:00:00+00	2026-12-04 08:45:00+00	12000.00
180	2	5	2026-12-04 10:00:00+00	2026-12-04 11:50:00+00	12000.00
181	1	1	2026-12-05 01:00:00+00	2026-12-05 02:45:00+00	12000.00
182	2	1	2026-12-05 04:00:00+00	2026-12-05 05:50:00+00	12000.00
183	3	1	2026-12-05 07:00:00+00	2026-12-05 08:27:00+00	12000.00
184	4	1	2026-12-05 10:00:00+00	2026-12-05 11:59:00+00	12000.00
185	2	2	2026-12-05 01:00:00+00	2026-12-05 02:50:00+00	12000.00
186	3	2	2026-12-05 04:00:00+00	2026-12-05 05:27:00+00	12000.00
187	4	2	2026-12-05 07:00:00+00	2026-12-05 08:59:00+00	12000.00
188	5	2	2026-12-05 10:00:00+00	2026-12-05 12:14:00+00	12000.00
189	3	3	2026-12-05 01:00:00+00	2026-12-05 02:27:00+00	12000.00
190	4	3	2026-12-05 04:00:00+00	2026-12-05 05:59:00+00	12000.00
191	5	3	2026-12-05 07:00:00+00	2026-12-05 09:14:00+00	12000.00
192	6	3	2026-12-05 10:00:00+00	2026-12-05 11:55:00+00	12000.00
193	4	4	2026-12-05 01:00:00+00	2026-12-05 02:59:00+00	12000.00
194	5	4	2026-12-05 04:00:00+00	2026-12-05 06:14:00+00	12000.00
195	6	4	2026-12-05 07:00:00+00	2026-12-05 08:55:00+00	12000.00
196	1	4	2026-12-05 10:00:00+00	2026-12-05 11:45:00+00	12000.00
197	5	5	2026-12-05 01:00:00+00	2026-12-05 03:14:00+00	12000.00
198	6	5	2026-12-05 04:00:00+00	2026-12-05 05:55:00+00	12000.00
199	1	5	2026-12-05 07:00:00+00	2026-12-05 08:45:00+00	12000.00
200	2	5	2026-12-05 10:00:00+00	2026-12-05 11:50:00+00	12000.00
201	1	1	2026-12-06 01:00:00+00	2026-12-06 02:45:00+00	12000.00
202	2	1	2026-12-06 04:00:00+00	2026-12-06 05:50:00+00	12000.00
203	3	1	2026-12-06 07:00:00+00	2026-12-06 08:27:00+00	12000.00
204	4	1	2026-12-06 10:00:00+00	2026-12-06 11:59:00+00	12000.00
205	2	2	2026-12-06 01:00:00+00	2026-12-06 02:50:00+00	12000.00
206	3	2	2026-12-06 04:00:00+00	2026-12-06 05:27:00+00	12000.00
207	4	2	2026-12-06 07:00:00+00	2026-12-06 08:59:00+00	12000.00
208	5	2	2026-12-06 10:00:00+00	2026-12-06 12:14:00+00	12000.00
209	3	3	2026-12-06 01:00:00+00	2026-12-06 02:27:00+00	12000.00
210	4	3	2026-12-06 04:00:00+00	2026-12-06 05:59:00+00	12000.00
211	5	3	2026-12-06 07:00:00+00	2026-12-06 09:14:00+00	12000.00
212	6	3	2026-12-06 10:00:00+00	2026-12-06 11:55:00+00	12000.00
213	4	4	2026-12-06 01:00:00+00	2026-12-06 02:59:00+00	12000.00
214	5	4	2026-12-06 04:00:00+00	2026-12-06 06:14:00+00	12000.00
215	6	4	2026-12-06 07:00:00+00	2026-12-06 08:55:00+00	12000.00
216	1	4	2026-12-06 10:00:00+00	2026-12-06 11:45:00+00	12000.00
217	5	5	2026-12-06 01:00:00+00	2026-12-06 03:14:00+00	12000.00
218	6	5	2026-12-06 04:00:00+00	2026-12-06 05:55:00+00	12000.00
219	1	5	2026-12-06 07:00:00+00	2026-12-06 08:45:00+00	12000.00
220	2	5	2026-12-06 10:00:00+00	2026-12-06 11:50:00+00	12000.00
221	1	1	2026-12-07 01:00:00+00	2026-12-07 02:45:00+00	12000.00
222	2	1	2026-12-07 04:00:00+00	2026-12-07 05:50:00+00	12000.00
223	3	1	2026-12-07 07:00:00+00	2026-12-07 08:27:00+00	12000.00
224	4	1	2026-12-07 10:00:00+00	2026-12-07 11:59:00+00	12000.00
225	2	2	2026-12-07 01:00:00+00	2026-12-07 02:50:00+00	12000.00
226	3	2	2026-12-07 04:00:00+00	2026-12-07 05:27:00+00	12000.00
227	4	2	2026-12-07 07:00:00+00	2026-12-07 08:59:00+00	12000.00
228	5	2	2026-12-07 10:00:00+00	2026-12-07 12:14:00+00	12000.00
229	3	3	2026-12-07 01:00:00+00	2026-12-07 02:27:00+00	12000.00
230	4	3	2026-12-07 04:00:00+00	2026-12-07 05:59:00+00	12000.00
231	5	3	2026-12-07 07:00:00+00	2026-12-07 09:14:00+00	12000.00
232	6	3	2026-12-07 10:00:00+00	2026-12-07 11:55:00+00	12000.00
233	4	4	2026-12-07 01:00:00+00	2026-12-07 02:59:00+00	12000.00
234	5	4	2026-12-07 04:00:00+00	2026-12-07 06:14:00+00	12000.00
235	6	4	2026-12-07 07:00:00+00	2026-12-07 08:55:00+00	12000.00
236	1	4	2026-12-07 10:00:00+00	2026-12-07 11:45:00+00	12000.00
237	5	5	2026-12-07 01:00:00+00	2026-12-07 03:14:00+00	12000.00
238	6	5	2026-12-07 04:00:00+00	2026-12-07 05:55:00+00	12000.00
239	1	5	2026-12-07 07:00:00+00	2026-12-07 08:45:00+00	12000.00
240	2	5	2026-12-07 10:00:00+00	2026-12-07 11:50:00+00	12000.00
241	1	1	2026-12-08 01:00:00+00	2026-12-08 02:45:00+00	12000.00
242	2	1	2026-12-08 04:00:00+00	2026-12-08 05:50:00+00	12000.00
243	3	1	2026-12-08 07:00:00+00	2026-12-08 08:27:00+00	12000.00
244	4	1	2026-12-08 10:00:00+00	2026-12-08 11:59:00+00	12000.00
245	2	2	2026-12-08 01:00:00+00	2026-12-08 02:50:00+00	12000.00
246	3	2	2026-12-08 04:00:00+00	2026-12-08 05:27:00+00	12000.00
247	4	2	2026-12-08 07:00:00+00	2026-12-08 08:59:00+00	12000.00
248	5	2	2026-12-08 10:00:00+00	2026-12-08 12:14:00+00	12000.00
249	3	3	2026-12-08 01:00:00+00	2026-12-08 02:27:00+00	12000.00
250	4	3	2026-12-08 04:00:00+00	2026-12-08 05:59:00+00	12000.00
251	5	3	2026-12-08 07:00:00+00	2026-12-08 09:14:00+00	12000.00
252	6	3	2026-12-08 10:00:00+00	2026-12-08 11:55:00+00	12000.00
253	4	4	2026-12-08 01:00:00+00	2026-12-08 02:59:00+00	12000.00
254	5	4	2026-12-08 04:00:00+00	2026-12-08 06:14:00+00	12000.00
255	6	4	2026-12-08 07:00:00+00	2026-12-08 08:55:00+00	12000.00
256	1	4	2026-12-08 10:00:00+00	2026-12-08 11:45:00+00	12000.00
257	5	5	2026-12-08 01:00:00+00	2026-12-08 03:14:00+00	12000.00
258	6	5	2026-12-08 04:00:00+00	2026-12-08 05:55:00+00	12000.00
259	1	5	2026-12-08 07:00:00+00	2026-12-08 08:45:00+00	12000.00
260	2	5	2026-12-08 10:00:00+00	2026-12-08 11:50:00+00	12000.00
261	1	1	2026-12-09 01:00:00+00	2026-12-09 02:45:00+00	12000.00
262	2	1	2026-12-09 04:00:00+00	2026-12-09 05:50:00+00	12000.00
263	3	1	2026-12-09 07:00:00+00	2026-12-09 08:27:00+00	12000.00
264	4	1	2026-12-09 10:00:00+00	2026-12-09 11:59:00+00	12000.00
265	2	2	2026-12-09 01:00:00+00	2026-12-09 02:50:00+00	12000.00
266	3	2	2026-12-09 04:00:00+00	2026-12-09 05:27:00+00	12000.00
267	4	2	2026-12-09 07:00:00+00	2026-12-09 08:59:00+00	12000.00
268	5	2	2026-12-09 10:00:00+00	2026-12-09 12:14:00+00	12000.00
269	3	3	2026-12-09 01:00:00+00	2026-12-09 02:27:00+00	12000.00
270	4	3	2026-12-09 04:00:00+00	2026-12-09 05:59:00+00	12000.00
271	5	3	2026-12-09 07:00:00+00	2026-12-09 09:14:00+00	12000.00
272	6	3	2026-12-09 10:00:00+00	2026-12-09 11:55:00+00	12000.00
273	4	4	2026-12-09 01:00:00+00	2026-12-09 02:59:00+00	12000.00
274	5	4	2026-12-09 04:00:00+00	2026-12-09 06:14:00+00	12000.00
275	6	4	2026-12-09 07:00:00+00	2026-12-09 08:55:00+00	12000.00
276	1	4	2026-12-09 10:00:00+00	2026-12-09 11:45:00+00	12000.00
277	5	5	2026-12-09 01:00:00+00	2026-12-09 03:14:00+00	12000.00
278	6	5	2026-12-09 04:00:00+00	2026-12-09 05:55:00+00	12000.00
279	1	5	2026-12-09 07:00:00+00	2026-12-09 08:45:00+00	12000.00
280	2	5	2026-12-09 10:00:00+00	2026-12-09 11:50:00+00	12000.00
\.


--
-- Data for Name: theater_rooms; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.theater_rooms (room_id, room_name) FROM stdin;
1	Hall 1
2	Hall 2
3	Hall 3
4	Hall 4
5	Hall 5
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (user_id, username, password_hash, role, created_at) FROM stdin;
1	admin	pbkdf2:sha256:600000$173528b654ee4462$d480b4f9fe069011000fc1e121ceed936139e5a23df83f25ecb24f5052ee2b7a	ADMIN	2026-11-26 07:25:13.735861+00
2	customer1	pbkdf2:sha256:600000$c2dcfc0b5cb72d2c$ba2bffe6f6ce01dc3fefcbe1a3e9c868666df4caf1bdb2ca94a7e91262cd1b02	CUSTOMER	2026-11-26 07:25:13.735861+00
3	customer2	pbkdf2:sha256:600000$f545d159cd8e6ced$349d9a1c35a07a870158bb5460acd39d37eb39610f0a42b04e87636d87568a55	CUSTOMER	2026-11-26 07:25:13.735861+00
\.


--
-- Name: booking_seats_booking_seat_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.booking_seats_booking_seat_id_seq', 1, false);


--
-- Name: bookings_booking_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.bookings_booking_id_seq', 1, false);


--
-- Name: movies_movie_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.movies_movie_id_seq', 6, true);


--
-- Name: seats_seat_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.seats_seat_id_seq', 250, true);


--
-- Name: showtimes_showtime_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.showtimes_showtime_id_seq', 280, true);


--
-- Name: theater_rooms_room_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.theater_rooms_room_id_seq', 5, true);


--
-- Name: users_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_user_id_seq', 3, true);


--
-- Name: booking_seats booking_seats_booking_id_seat_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.booking_seats
    ADD CONSTRAINT booking_seats_booking_id_seat_id_key UNIQUE (booking_id, seat_id);


--
-- Name: booking_seats booking_seats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.booking_seats
    ADD CONSTRAINT booking_seats_pkey PRIMARY KEY (booking_seat_id);


--
-- Name: booking_seats booking_seats_showtime_seat_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.booking_seats
    ADD CONSTRAINT booking_seats_showtime_seat_key UNIQUE (showtime_id, seat_id);


--
-- Name: bookings bookings_id_showtime_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_id_showtime_key UNIQUE (booking_id, showtime_id);


--
-- Name: bookings bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_pkey PRIMARY KEY (booking_id);


--
-- Name: movies movies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movies
    ADD CONSTRAINT movies_pkey PRIMARY KEY (movie_id);


--
-- Name: seats seats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seats
    ADD CONSTRAINT seats_pkey PRIMARY KEY (seat_id);


--
-- Name: seats seats_room_id_seat_row_seat_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seats
    ADD CONSTRAINT seats_room_id_seat_row_seat_number_key UNIQUE (room_id, seat_row, seat_number);


--
-- Name: showtimes showtimes_no_room_overlap; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.showtimes
    ADD CONSTRAINT showtimes_no_room_overlap EXCLUDE USING gist (room_id WITH =, tstzrange(starts_at, ends_at, '[)'::text) WITH &&);


--
-- Name: showtimes showtimes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.showtimes
    ADD CONSTRAINT showtimes_pkey PRIMARY KEY (showtime_id);


--
-- Name: theater_rooms theater_rooms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.theater_rooms
    ADD CONSTRAINT theater_rooms_pkey PRIMARY KEY (room_id);


--
-- Name: theater_rooms theater_rooms_room_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.theater_rooms
    ADD CONSTRAINT theater_rooms_room_name_key UNIQUE (room_name);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: idx_booking_seats_seat; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_booking_seats_seat ON public.booking_seats USING btree (seat_id);


--
-- Name: idx_bookings_pending_expiry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bookings_pending_expiry ON public.bookings USING btree (expires_at) WHERE (((status)::text = 'BOOKED'::text) AND ((payment_status)::text = 'UNPAID'::text));


--
-- Name: idx_bookings_showtime_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bookings_showtime_status ON public.bookings USING btree (showtime_id, status);


--
-- Name: idx_bookings_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bookings_user ON public.bookings USING btree (user_id, booked_at DESC);


--
-- Name: idx_showtimes_movie_start; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_showtimes_movie_start ON public.showtimes USING btree (movie_id, starts_at);


--
-- Name: idx_showtimes_room_start; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_showtimes_room_start ON public.showtimes USING btree (room_id, starts_at);


--
-- Name: users_username_lower_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX users_username_lower_key ON public.users USING btree (lower((username)::text));


--
-- Name: booking_seats trg_booking_seats_consistency; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER trg_booking_seats_consistency AFTER INSERT ON public.booking_seats DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.booking_check_consistency();


--
-- Name: booking_seats trg_booking_seats_protect_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_booking_seats_protect_delete BEFORE DELETE ON public.booking_seats FOR EACH ROW EXECUTE FUNCTION public.booking_seats_protect_delete();


--
-- Name: booking_seats trg_booking_seats_validate; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_booking_seats_validate BEFORE INSERT OR UPDATE ON public.booking_seats FOR EACH ROW EXECUTE FUNCTION public.booking_seats_validate();


--
-- Name: bookings trg_bookings_release_seats; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bookings_release_seats AFTER UPDATE OF status ON public.bookings FOR EACH ROW EXECUTE FUNCTION public.bookings_release_seats();


--
-- Name: bookings trg_bookings_validate; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bookings_validate BEFORE INSERT OR UPDATE ON public.bookings FOR EACH ROW EXECUTE FUNCTION public.bookings_validate();


--
-- Name: bookings trg_bookings_z_consistency; Type: TRIGGER; Schema: public; Owner: -
--

CREATE CONSTRAINT TRIGGER trg_bookings_z_consistency AFTER INSERT OR UPDATE OF status ON public.bookings DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.booking_check_consistency();


--
-- Name: bookings trg_bookings_z_version_showtime; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bookings_z_version_showtime BEFORE INSERT ON public.bookings FOR EACH ROW EXECUTE FUNCTION public.bookings_version_first_showtime_reference();


--
-- Name: showtimes trg_showtimes_default_end_time; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_showtimes_default_end_time BEFORE INSERT OR UPDATE ON public.showtimes FOR EACH ROW EXECUTE FUNCTION public.showtimes_default_end_time();


--
-- Name: showtimes trg_showtimes_protect_booked; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_showtimes_protect_booked BEFORE UPDATE ON public.showtimes FOR EACH ROW EXECUTE FUNCTION public.showtimes_protect_booked();


--
-- Name: booking_seats booking_seats_booking_showtime_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.booking_seats
    ADD CONSTRAINT booking_seats_booking_showtime_fkey FOREIGN KEY (booking_id, showtime_id) REFERENCES public.bookings(booking_id, showtime_id) ON DELETE CASCADE;


--
-- Name: booking_seats booking_seats_seat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.booking_seats
    ADD CONSTRAINT booking_seats_seat_id_fkey FOREIGN KEY (seat_id) REFERENCES public.seats(seat_id) ON DELETE RESTRICT;


--
-- Name: bookings bookings_showtime_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_showtime_id_fkey FOREIGN KEY (showtime_id) REFERENCES public.showtimes(showtime_id) ON DELETE RESTRICT;


--
-- Name: bookings bookings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE RESTRICT;


--
-- Name: seats seats_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seats
    ADD CONSTRAINT seats_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.theater_rooms(room_id) ON DELETE RESTRICT;


--
-- Name: showtimes showtimes_movie_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.showtimes
    ADD CONSTRAINT showtimes_movie_id_fkey FOREIGN KEY (movie_id) REFERENCES public.movies(movie_id) ON DELETE RESTRICT;


--
-- Name: showtimes showtimes_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.showtimes
    ADD CONSTRAINT showtimes_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.theater_rooms(room_id) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict ehAKKosbq0B5g0CqyXpM0ABb3ruIZfMNYnHicfUQDCslTry2YcgChWxxNvS7P1G

