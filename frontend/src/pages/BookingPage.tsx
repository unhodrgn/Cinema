import { useEffect, useState } from "react";
import { loginUrl } from "../../js/auth.js";
import {
  calculateTotal,
  formatSelectedSeats,
  seatLabel,
  takenSeatsMessage,
} from "../../js/seats.js";
import { formatMoney, formatDateTimeRange, isIdText } from "../../js/format.js";
import { auth, errorMessage, get, post } from "../services/apiClient";
import { useBookingStore } from "../store/useBookingStore";
import { SeatMap } from "../features/booking/SeatMap";
import { BookingSteps } from "../features/booking/BookingSteps";
import { Poster } from "../features/movies/MovieCard";
import type { AvailableSeat, Booking, Showtime } from "../types/cinema";

type MapData = { screening: Showtime; seats: AvailableSeat[] };
export function BookingPage() {
  const id = new URLSearchParams(location.search).get("screening_id");
  const path = "/api/screenings/" + id + "/seats";
  const { selection, reconcile, toggle } = useBookingStore();
  const [data, setData] = useState<MapData>();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (!isIdText(id)) return;
    let active = true;
    get<MapData>(path)
      .then((data) => {
        if (active) {
          reconcile(data.seats);
          setData(data);
        }
      })
      .catch((error) => active && setMessage(errorMessage(error)));
    return () => {
      active = false;
    };
  }, [path]);
  if (!isIdText(id))
    return <p role="alert">Invalid or missing screening ID.</p>;
  const chosen =
    data?.seats.filter((s) => s.is_available && selection.has(s.seat_id)) || [];
  async function reserve() {
    const seatIds = chosen.map((s) => s.seat_id);
    if (busy || !seatIds.length) return;
    setBusy(true);
    setMessage("");
    try {
      const user = await auth.currentUser();
      if (!user) {
        location.assign(
          loginUrl(
            "/seats.html?screening_id=" +
              id +
              "&selected=" +
              formatSelectedSeats(seatIds),
          ),
        );
        return;
      }
      if (user.role !== "CUSTOMER") {
        setMessage("Only customer accounts can make bookings.");
        return;
      }
      const { booking } = await post<{ booking: Booking }>("/api/bookings", {
        screening_id: Number(id),
        seat_ids: seatIds,
      });
      location.assign("/booking.html?id=" + booking.booking_id);
    } catch (error) {
      setMessage(errorMessage(error));
      try {
        const fresh = await get<MapData>(path);
        const removed = fresh.seats
          .filter((s) => selection.has(s.seat_id) && !s.is_available)
          .map(seatLabel);
        reconcile(fresh.seats);
        setData(fresh);
        if (removed.length) setMessage(takenSeatsMessage(removed));
      } catch (reloadError) {
        setMessage(errorMessage(reloadError));
        setData(undefined);
      }
    } finally {
      setBusy(false);
    }
  }
  const s = data?.screening;
  return (
    <>
      <BookingSteps current="Seats" />
      <h1>Select Seats</h1>
      {message && (
        <p className="message message-error" role="alert">
          {message}
        </p>
      )}
      {!data && !message && <p role="status">Loading seats…</p>}
      {s && data && (
        <>
          <div className="card screening-info">
            <Poster title={s.title} url={s.poster_url} size="sm" />
            <div>
              <h2>{s.title}</h2>
              <p>
                {formatDateTimeRange(s.starts_at, s.ends_at)} · {s.room_name}
              </p>
              <p>Price per seat: {formatMoney(s.ticket_price)}</p>
              {s.has_started && <p>This screening has already started.</p>}
            </div>
          </div>
          <section className="seat-layout">
            <SeatMap
              seats={data.seats}
              selection={selection}
              toggle={toggle}
              disabled={s.has_started || busy}
            />
            <aside
              className="card seat-summary-bar"
              aria-label="Booking summary"
            >
              <h2>Summary</h2>
              <dl className="summary-list">
                <dt>Seats</dt>
                <dd>{chosen.map(seatLabel).join(", ") || "None"}</dd>
                <dt>Tickets</dt>
                <dd>
                  {chosen.length} × {formatMoney(s.ticket_price)}
                </dd>
                <dt>Total</dt>
                <dd>
                  <strong>
                    {formatMoney(calculateTotal(chosen.length, s.ticket_price))}
                  </strong>
                </dd>
              </dl>
              <button
                className="button"
                disabled={busy || s.has_started || !chosen.length}
                onClick={reserve}
              >
                Proceed to booking
              </button>
            </aside>
          </section>
        </>
      )}
    </>
  );
}
