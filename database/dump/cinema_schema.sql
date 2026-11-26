--
-- PostgreSQL database dump
--

\restrict EaTtKmJmEeHaHjq60Tr8zqGpIpnXt0FbA0k9OZar5jlHUJhgnyMsdIjsh8nvaKz

-- Dumped from database version 18.7 (Debian 18.7-1.pgdg13+5)
-- Dumped by pg_dump version 18.7 (Debian 18.7-1.pgdg13+5)

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
-- Name: cinema_username_is_valid(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cinema_username_is_valid(value text) RETURNS boolean
    LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
    SET search_path TO 'pg_catalog'
    AS $_$
    SELECT char_length(value) BETWEEN 1 AND 60 AND value IS NFKC NORMALIZED
-- BEGIN GENERATED POLICY
    AND (value COLLATE "C" ~ $rx$^[0-9A-Za-zªµºÀ-ÖØ-öø-ˁˆ-ˑˠ-ˤˬˮͰ-ʹͶ-ͷͺ-ͽͿΆΈ-ΊΌΎ-ΡΣ-ϵϷ-ҁҊ-ԯԱ-Ֆՙՠ-ֈא-תׯ-ײؠ-ي٠-٩ٮ-ٯٱ-ۓەۥ-ۦۮ-ۼۿܐܒ-ܯݍ-ޥޱ߀-ߪߴ-ߵߺࠀ-ࠕࠚࠤࠨࡀ-ࡘࡠ-ࡪࡰ-ࢇࢉ-ࢎࢠ-ࣉऄ-हऽॐक़-ॡ०-९ॱ-ঀঅ-ঌএ-ঐও-নপ-রলশ-হঽৎড়-ঢ়য়-ৡ০-ৱৼਅ-ਊਏ-ਐਓ-ਨਪ-ਰਲ-ਲ਼ਵ-ਸ਼ਸ-ਹਖ਼-ੜਫ਼੦-੯ੲ-ੴઅ-ઍએ-ઑઓ-નપ-રલ-ળવ-હઽૐૠ-ૡ૦-૯ૹଅ-ଌଏ-ଐଓ-ନପ-ରଲ-ଳଵ-ହଽଡ଼-ଢ଼ୟ-ୡ୦-୯ୱஃஅ-ஊஎ-ஐஒ-கங-சஜஞ-டண-தந-பம-ஹௐ௦-௯అ-ఌఎ-ఐఒ-నప-హఽౘ-ౚౝౠ-ౡ౦-౯ಀಅ-ಌಎ-ಐಒ-ನಪ-ಳವ-ಹಽೝ-ೞೠ-ೡ೦-೯ೱ-ೲഄ-ഌഎ-ഐഒ-ഺഽൎൔ-ൖൟ-ൡ൦-൯ൺ-ൿඅ-ඖක-නඳ-රලව-ෆ෦-෯ก-ะา-ำเ-ๆ๐-๙ກ-ຂຄຆ-ຊຌ-ຣລວ-ະາ-ຳຽເ-ໄໆ໐-໙ໜ-ໟༀ༠-༩ཀ-ཇཉ-ཬྈ-ྌက-ဪဿ-၉ၐ-ၕၚ-ၝၡၥ-ၦၮ-ၰၵ-ႁႎ႐-႙Ⴀ-ჅჇჍა-ჺჼ-ᅞᅡ-ቈቊ-ቍቐ-ቖቘቚ-ቝበ-ኈኊ-ኍነ-ኰኲ-ኵኸ-ኾዀዂ-ዅወ-ዖዘ-ጐጒ-ጕጘ-ፚᎀ-ᎏᎠ-Ᏽᏸ-ᏽᐁ-ᙬᙯ-ᙿᚁ-ᚚᚠ-ᛪᛱ-ᛸᜀ-ᜑᜟ-ᜱᝀ-ᝑᝠ-ᝬᝮ-ᝰក-ឳៗៜ០-៩᠐-᠙ᠠ-ᡸᢀ-ᢄᢇ-ᢨᢪᢰ-ᣵᤀ-ᤞ᥆-ᥭᥰ-ᥴᦀ-ᦫᦰ-ᧉ᧐-᧙ᨀ-ᨖᨠ-ᩔ᪀-᪉᪐-᪙ᪧᬅ-ᬳᭅ-ᭌ᭐-᭙ᮃ-ᮠᮮ-ᯥᰀ-ᰣ᱀-᱉ᱍ-ᱽᲀ-ᲈᲐ-ᲺᲽ-Ჿᳩ-ᳬᳮ-ᳳᳵ-ᳶᳺᴀ-ᶿḀ-ἕἘ-Ἕἠ-ὅὈ-Ὅὐ-ὗὙὛὝὟ-ώᾀ-ᾴᾶ-ᾼιῂ-ῄῆ-ῌῐ-ΐῖ-Ίῠ-Ῥῲ-ῴῶ-ῼⁱⁿₐ-ₜℂℇℊ-ℓℕℙ-ℝℤΩℨK-ℭℯ-ℹℼ-ℿⅅ-ⅉⅎↃ-ↄⰀ-ⳤⳫ-ⳮⳲ-ⳳⴀ-ⴥⴧⴭⴰ-ⵧⵯⶀ-ⶖⶠ-ⶦⶨ-ⶮⶰ-ⶶⶸ-ⶾⷀ-ⷆⷈ-ⷎⷐ-ⷖⷘ-ⷞⸯ々-〆〱-〵〻-〼ぁ-ゖゝ-ゟァ-ヺー-ヿㄅ-ㄯㄱ-ㅣㅥ-ㆎㆠ-ㆿㇰ-ㇿ㐀-䶿一-ꒌꓐ-ꓽꔀ-ꘌꘐ-ꘫꙀ-ꙮꙿ-ꚝꚠ-ꛥꜗ-ꜟꜢ-ꞈꞋ-ꟊꟐ-ꟑꟓꟕ-ꟙꟲ-ꠁꠃ-ꠅꠇ-ꠊꠌ-ꠢꡀ-ꡳꢂ-ꢳ꣐-꣙ꣲ-ꣷꣻꣽ-ꣾ꤀-ꤥꤰ-ꥆꥠ-ꥼꦄ-ꦲꧏ-꧙ꧠ-ꧤꧦ-ꧾꨀ-ꨨꩀ-ꩂꩄ-ꩋ꩐-꩙ꩠ-ꩶꩺꩾ-ꪯꪱꪵ-ꪶꪹ-ꪽꫀꫂꫛ-ꫝꫠ-ꫪꫲ-ꫴꬁ-ꬆꬉ-ꬎꬑ-ꬖꬠ-ꬦꬨ-ꬮꬰ-ꭚꭜ-ꭩꭰ-ꯢ꯰-꯹가-힣ힰ-ퟆퟋ-ퟻ豈-舘並-龎ﬀ-ﬆﬓ-ﬗיִײַ-ﬨשׁ-זּטּ-לּמּנּ-סּףּ-פּצּ-ﮱﯓ-ﴽﵐ-ﶏﶒ-ﷇﷰ-ﷻﹰ-ﹴﹶ-ﻼ０-９Ａ-Ｚａ-ｚｦ-ﾟﾡ-ﾾￂ-ￇￊ-ￏￒ-ￗￚ-ￜ𐀀-𐀋𐀍-𐀦𐀨-𐀺𐀼-𐀽𐀿-𐁍𐁐-𐁝𐂀-𐃺𐊀-𐊜𐊠-𐋐𐌀-𐌟𐌭-𐍀𐍂-𐍉𐍐-𐍵𐎀-𐎝𐎠-𐏃𐏈-𐏏𐐀-𐒝𐒠-𐒩𐒰-𐓓𐓘-𐓻𐔀-𐔧𐔰-𐕣𐕰-𐕺𐕼-𐖊𐖌-𐖒𐖔-𐖕𐖗-𐖡𐖣-𐖱𐖳-𐖹𐖻-𐖼𐘀-𐜶𐝀-𐝕𐝠-𐝧𐞀-𐞅𐞇-𐞰𐞲-𐞺𐠀-𐠅𐠈𐠊-𐠵𐠷-𐠸𐠼𐠿-𐡕𐡠-𐡶𐢀-𐢞𐣠-𐣲𐣴-𐣵𐤀-𐤕𐤠-𐤹𐦀-𐦷𐦾-𐦿𐨀𐨐-𐨓𐨕-𐨗𐨙-𐨵𐩠-𐩼𐪀-𐪜𐫀-𐫇𐫉-𐫤𐬀-𐬵𐭀-𐭕𐭠-𐭲𐮀-𐮑𐰀-𐱈𐲀-𐲲𐳀-𐳲𐴀-𐴣𐴰-𐴹𐺀-𐺩𐺰-𐺱𐼀-𐼜𐼧𐼰-𐽅𐽰-𐾁𐾰-𐿄𐿠-𐿶𑀃-𑀷𑁦-𑁯𑁱-𑁲𑁵𑂃-𑂯𑃐-𑃨𑃰-𑃹𑄃-𑄦𑄶-𑄿𑅄𑅇𑅐-𑅲𑅶𑆃-𑆲𑇁-𑇄𑇐-𑇚𑇜𑈀-𑈑𑈓-𑈫𑈿-𑉀𑊀-𑊆𑊈𑊊-𑊍𑊏-𑊝𑊟-𑊨𑊰-𑋞𑋰-𑋹𑌅-𑌌𑌏-𑌐𑌓-𑌨𑌪-𑌰𑌲-𑌳𑌵-𑌹𑌽𑍐𑍝-𑍡𑐀-𑐴𑑇-𑑊𑑐-𑑙𑑟-𑑡𑒀-𑒯𑓄-𑓅𑓇𑓐-𑓙𑖀-𑖮𑗘-𑗛𑘀-𑘯𑙄𑙐-𑙙𑚀-𑚪𑚸𑛀-𑛉𑜀-𑜚𑜰-𑜹𑝀-𑝆𑠀-𑠫𑢠-𑣩𑣿-𑤆𑤉𑤌-𑤓𑤕-𑤖𑤘-𑤯𑤿𑥁𑥐-𑥙𑦠-𑦧𑦪-𑧐𑧡𑧣𑨀𑨋-𑨲𑨺𑩐𑩜-𑪉𑪝𑪰-𑫸𑰀-𑰈𑰊-𑰮𑱀𑱐-𑱙𑱲-𑲏𑴀-𑴆𑴈-𑴉𑴋-𑴰𑵆𑵐-𑵙𑵠-𑵥𑵧-𑵨𑵪-𑶉𑶘𑶠-𑶩𑻠-𑻲𑼂𑼄-𑼐𑼒-𑼳𑽐-𑽙𑾰𒀀-𒎙𒒀-𒕃𒾐-𒿰𓀀-𓐯𓑁-𓑆𔐀-𔙆𖠀-𖨸𖩀-𖩞𖩠-𖩩𖩰-𖪾𖫀-𖫉𖫐-𖫭𖬀-𖬯𖭀-𖭃𖭐-𖭙𖭣-𖭷𖭽-𖮏𖹀-𖹿𖼀-𖽊𖽐𖾓-𖾟𖿠-𖿡𖿣𗀀-𘟷𘠀-𘳕𘴀-𘴈𚿰-𚿳𚿵-𚿻𚿽-𚿾𛀀-𛄢𛄲𛅐-𛅒𛅕𛅤-𛅧𛅰-𛋻𛰀-𛱪𛱰-𛱼𛲀-𛲈𛲐-𛲙𝐀-𝑔𝑖-𝒜𝒞-𝒟𝒢𝒥-𝒦𝒩-𝒬𝒮-𝒹𝒻𝒽-𝓃𝓅-𝔅𝔇-𝔊𝔍-𝔔𝔖-𝔜𝔞-𝔹𝔻-𝔾𝕀-𝕄𝕆𝕊-𝕐𝕒-𝚥𝚨-𝛀𝛂-𝛚𝛜-𝛺𝛼-𝜔𝜖-𝜴𝜶-𝝎𝝐-𝝮𝝰-𝞈𝞊-𝞨𝞪-𝟂𝟄-𝟋𝟎-𝟿𝼀-𝼞𝼥-𝼪𞀰-𞁭𞄀-𞄬𞄷-𞄽𞅀-𞅉𞅎𞊐-𞊭𞋀-𞋫𞋰-𞋹𞓐-𞓫𞓰-𞓹𞟠-𞟦𞟨-𞟫𞟭-𞟮𞟰-𞟾𞠀-𞣄𞤀-𞥃𞥋𞥐-𞥙𞸀-𞸃𞸅-𞸟𞸡-𞸢𞸤𞸧𞸩-𞸲𞸴-𞸷𞸹𞸻𞹂𞹇𞹉𞹋𞹍-𞹏𞹑-𞹒𞹔𞹗𞹙𞹛𞹝𞹟𞹡-𞹢𞹤𞹧-𞹪𞹬-𞹲𞹴-𞹷𞹹-𞹼𞹾𞺀-𞺉𞺋-𞺛𞺡-𞺣𞺥-𞺩𞺫-𞺻🯰-🯹𠀀-𪛟𪜀-𫜹𫝀-𫠝𫠠-𬺡𬺰-𮯠丽-𪘀𰀀-𱍊𱍐-𲎯][0-9A-Za-zªµºÀ-ÖØ-öø-ˁˆ-ˑˠ-ˤˬˮͰ-ʹͶ-ͷͺ-ͽͿΆΈ-ΊΌΎ-ΡΣ-ϵϷ-ҁҊ-ԯԱ-Ֆՙՠ-ֈא-תׯ-ײؠ-ي٠-٩ٮ-ٯٱ-ۓەۥ-ۦۮ-ۼۿܐܒ-ܯݍ-ޥޱ߀-ߪߴ-ߵߺࠀ-ࠕࠚࠤࠨࡀ-ࡘࡠ-ࡪࡰ-ࢇࢉ-ࢎࢠ-ࣉऄ-हऽॐक़-ॡ०-९ॱ-ঀঅ-ঌএ-ঐও-নপ-রলশ-হঽৎড়-ঢ়য়-ৡ০-ৱৼਅ-ਊਏ-ਐਓ-ਨਪ-ਰਲ-ਲ਼ਵ-ਸ਼ਸ-ਹਖ਼-ੜਫ਼੦-੯ੲ-ੴઅ-ઍએ-ઑઓ-નપ-રલ-ળવ-હઽૐૠ-ૡ૦-૯ૹଅ-ଌଏ-ଐଓ-ନପ-ରଲ-ଳଵ-ହଽଡ଼-ଢ଼ୟ-ୡ୦-୯ୱஃஅ-ஊஎ-ஐஒ-கங-சஜஞ-டண-தந-பம-ஹௐ௦-௯అ-ఌఎ-ఐఒ-నప-హఽౘ-ౚౝౠ-ౡ౦-౯ಀಅ-ಌಎ-ಐಒ-ನಪ-ಳವ-ಹಽೝ-ೞೠ-ೡ೦-೯ೱ-ೲഄ-ഌഎ-ഐഒ-ഺഽൎൔ-ൖൟ-ൡ൦-൯ൺ-ൿඅ-ඖක-නඳ-රලව-ෆ෦-෯ก-ะา-ำเ-ๆ๐-๙ກ-ຂຄຆ-ຊຌ-ຣລວ-ະາ-ຳຽເ-ໄໆ໐-໙ໜ-ໟༀ༠-༩ཀ-ཇཉ-ཬྈ-ྌက-ဪဿ-၉ၐ-ၕၚ-ၝၡၥ-ၦၮ-ၰၵ-ႁႎ႐-႙Ⴀ-ჅჇჍა-ჺჼ-ᅞᅡ-ቈቊ-ቍቐ-ቖቘቚ-ቝበ-ኈኊ-ኍነ-ኰኲ-ኵኸ-ኾዀዂ-ዅወ-ዖዘ-ጐጒ-ጕጘ-ፚᎀ-ᎏᎠ-Ᏽᏸ-ᏽᐁ-ᙬᙯ-ᙿᚁ-ᚚᚠ-ᛪᛱ-ᛸᜀ-ᜑᜟ-ᜱᝀ-ᝑᝠ-ᝬᝮ-ᝰក-ឳៗៜ០-៩᠐-᠙ᠠ-ᡸᢀ-ᢄᢇ-ᢨᢪᢰ-ᣵᤀ-ᤞ᥆-ᥭᥰ-ᥴᦀ-ᦫᦰ-ᧉ᧐-᧙ᨀ-ᨖᨠ-ᩔ᪀-᪉᪐-᪙ᪧᬅ-ᬳᭅ-ᭌ᭐-᭙ᮃ-ᮠᮮ-ᯥᰀ-ᰣ᱀-᱉ᱍ-ᱽᲀ-ᲈᲐ-ᲺᲽ-Ჿᳩ-ᳬᳮ-ᳳᳵ-ᳶᳺᴀ-ᶿḀ-ἕἘ-Ἕἠ-ὅὈ-Ὅὐ-ὗὙὛὝὟ-ώᾀ-ᾴᾶ-ᾼιῂ-ῄῆ-ῌῐ-ΐῖ-Ίῠ-Ῥῲ-ῴῶ-ῼⁱⁿₐ-ₜℂℇℊ-ℓℕℙ-ℝℤΩℨK-ℭℯ-ℹℼ-ℿⅅ-ⅉⅎↃ-ↄⰀ-ⳤⳫ-ⳮⳲ-ⳳⴀ-ⴥⴧⴭⴰ-ⵧⵯⶀ-ⶖⶠ-ⶦⶨ-ⶮⶰ-ⶶⶸ-ⶾⷀ-ⷆⷈ-ⷎⷐ-ⷖⷘ-ⷞⸯ々-〆〱-〵〻-〼ぁ-ゖゝ-ゟァ-ヺー-ヿㄅ-ㄯㄱ-ㅣㅥ-ㆎㆠ-ㆿㇰ-ㇿ㐀-䶿一-ꒌꓐ-ꓽꔀ-ꘌꘐ-ꘫꙀ-ꙮꙿ-ꚝꚠ-ꛥꜗ-ꜟꜢ-ꞈꞋ-ꟊꟐ-ꟑꟓꟕ-ꟙꟲ-ꠁꠃ-ꠅꠇ-ꠊꠌ-ꠢꡀ-ꡳꢂ-ꢳ꣐-꣙ꣲ-ꣷꣻꣽ-ꣾ꤀-ꤥꤰ-ꥆꥠ-ꥼꦄ-ꦲꧏ-꧙ꧠ-ꧤꧦ-ꧾꨀ-ꨨꩀ-ꩂꩄ-ꩋ꩐-꩙ꩠ-ꩶꩺꩾ-ꪯꪱꪵ-ꪶꪹ-ꪽꫀꫂꫛ-ꫝꫠ-ꫪꫲ-ꫴꬁ-ꬆꬉ-ꬎꬑ-ꬖꬠ-ꬦꬨ-ꬮꬰ-ꭚꭜ-ꭩꭰ-ꯢ꯰-꯹가-힣ힰ-ퟆퟋ-ퟻ豈-舘並-龎ﬀ-ﬆﬓ-ﬗיִײַ-ﬨשׁ-זּטּ-לּמּנּ-סּףּ-פּצּ-ﮱﯓ-ﴽﵐ-ﶏﶒ-ﷇﷰ-ﷻﹰ-ﹴﹶ-ﻼ０-９Ａ-Ｚａ-ｚｦ-ﾟﾡ-ﾾￂ-ￇￊ-ￏￒ-ￗￚ-ￜ𐀀-𐀋𐀍-𐀦𐀨-𐀺𐀼-𐀽𐀿-𐁍𐁐-𐁝𐂀-𐃺𐊀-𐊜𐊠-𐋐𐌀-𐌟𐌭-𐍀𐍂-𐍉𐍐-𐍵𐎀-𐎝𐎠-𐏃𐏈-𐏏𐐀-𐒝𐒠-𐒩𐒰-𐓓𐓘-𐓻𐔀-𐔧𐔰-𐕣𐕰-𐕺𐕼-𐖊𐖌-𐖒𐖔-𐖕𐖗-𐖡𐖣-𐖱𐖳-𐖹𐖻-𐖼𐘀-𐜶𐝀-𐝕𐝠-𐝧𐞀-𐞅𐞇-𐞰𐞲-𐞺𐠀-𐠅𐠈𐠊-𐠵𐠷-𐠸𐠼𐠿-𐡕𐡠-𐡶𐢀-𐢞𐣠-𐣲𐣴-𐣵𐤀-𐤕𐤠-𐤹𐦀-𐦷𐦾-𐦿𐨀𐨐-𐨓𐨕-𐨗𐨙-𐨵𐩠-𐩼𐪀-𐪜𐫀-𐫇𐫉-𐫤𐬀-𐬵𐭀-𐭕𐭠-𐭲𐮀-𐮑𐰀-𐱈𐲀-𐲲𐳀-𐳲𐴀-𐴣𐴰-𐴹𐺀-𐺩𐺰-𐺱𐼀-𐼜𐼧𐼰-𐽅𐽰-𐾁𐾰-𐿄𐿠-𐿶𑀃-𑀷𑁦-𑁯𑁱-𑁲𑁵𑂃-𑂯𑃐-𑃨𑃰-𑃹𑄃-𑄦𑄶-𑄿𑅄𑅇𑅐-𑅲𑅶𑆃-𑆲𑇁-𑇄𑇐-𑇚𑇜𑈀-𑈑𑈓-𑈫𑈿-𑉀𑊀-𑊆𑊈𑊊-𑊍𑊏-𑊝𑊟-𑊨𑊰-𑋞𑋰-𑋹𑌅-𑌌𑌏-𑌐𑌓-𑌨𑌪-𑌰𑌲-𑌳𑌵-𑌹𑌽𑍐𑍝-𑍡𑐀-𑐴𑑇-𑑊𑑐-𑑙𑑟-𑑡𑒀-𑒯𑓄-𑓅𑓇𑓐-𑓙𑖀-𑖮𑗘-𑗛𑘀-𑘯𑙄𑙐-𑙙𑚀-𑚪𑚸𑛀-𑛉𑜀-𑜚𑜰-𑜹𑝀-𑝆𑠀-𑠫𑢠-𑣩𑣿-𑤆𑤉𑤌-𑤓𑤕-𑤖𑤘-𑤯𑤿𑥁𑥐-𑥙𑦠-𑦧𑦪-𑧐𑧡𑧣𑨀𑨋-𑨲𑨺𑩐𑩜-𑪉𑪝𑪰-𑫸𑰀-𑰈𑰊-𑰮𑱀𑱐-𑱙𑱲-𑲏𑴀-𑴆𑴈-𑴉𑴋-𑴰𑵆𑵐-𑵙𑵠-𑵥𑵧-𑵨𑵪-𑶉𑶘𑶠-𑶩𑻠-𑻲𑼂𑼄-𑼐𑼒-𑼳𑽐-𑽙𑾰𒀀-𒎙𒒀-𒕃𒾐-𒿰𓀀-𓐯𓑁-𓑆𔐀-𔙆𖠀-𖨸𖩀-𖩞𖩠-𖩩𖩰-𖪾𖫀-𖫉𖫐-𖫭𖬀-𖬯𖭀-𖭃𖭐-𖭙𖭣-𖭷𖭽-𖮏𖹀-𖹿𖼀-𖽊𖽐𖾓-𖾟𖿠-𖿡𖿣𗀀-𘟷𘠀-𘳕𘴀-𘴈𚿰-𚿳𚿵-𚿻𚿽-𚿾𛀀-𛄢𛄲𛅐-𛅒𛅕𛅤-𛅧𛅰-𛋻𛰀-𛱪𛱰-𛱼𛲀-𛲈𛲐-𛲙𝐀-𝑔𝑖-𝒜𝒞-𝒟𝒢𝒥-𝒦𝒩-𝒬𝒮-𝒹𝒻𝒽-𝓃𝓅-𝔅𝔇-𝔊𝔍-𝔔𝔖-𝔜𝔞-𝔹𝔻-𝔾𝕀-𝕄𝕆𝕊-𝕐𝕒-𝚥𝚨-𝛀𝛂-𝛚𝛜-𝛺𝛼-𝜔𝜖-𝜴𝜶-𝝎𝝐-𝝮𝝰-𝞈𝞊-𝞨𝞪-𝟂𝟄-𝟋𝟎-𝟿𝼀-𝼞𝼥-𝼪𞀰-𞁭𞄀-𞄬𞄷-𞄽𞅀-𞅉𞅎𞊐-𞊭𞋀-𞋫𞋰-𞋹𞓐-𞓫𞓰-𞓹𞟠-𞟦𞟨-𞟫𞟭-𞟮𞟰-𞟾𞠀-𞣄𞤀-𞥃𞥋𞥐-𞥙𞸀-𞸃𞸅-𞸟𞸡-𞸢𞸤𞸧𞸩-𞸲𞸴-𞸷𞸹𞸻𞹂𞹇𞹉𞹋𞹍-𞹏𞹑-𞹒𞹔𞹗𞹙𞹛𞹝𞹟𞹡-𞹢𞹤𞹧-𞹪𞹬-𞹲𞹴-𞹷𞹹-𞹼𞹾𞺀-𞺉𞺋-𞺛𞺡-𞺣𞺥-𞺩𞺫-𞺻🯰-🯹𠀀-𪛟𪜀-𫜹𫝀-𫠝𫠠-𬺡𬺰-𮯠丽-𪘀𰀀-𱍊𱍐-𲎯_.+-]*$$rx$
         OR value COLLATE "C" ~ $rx$^[A-Za-z0-9][A-Za-z0-9_+-]*([.][A-Za-z0-9_+-]+)*@[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?([.][A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)*[.][A-Za-z]([A-Za-z0-9-]*[A-Za-z0-9])?$$rx$)
-- END GENERATED POLICY
$_$;


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
    username character varying NOT NULL,
    password_hash text NOT NULL,
    role character varying(10) DEFAULT 'CUSTOMER'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT users_role_check CHECK (((role)::text = ANY ((ARRAY['CUSTOMER'::character varying, 'ADMIN'::character varying])::text[]))),
    CONSTRAINT users_username_format_check CHECK (public.cinema_username_is_valid((username)::text))
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

\unrestrict EaTtKmJmEeHaHjq60Tr8zqGpIpnXt0FbA0k9OZar5jlHUJhgnyMsdIjsh8nvaKz

