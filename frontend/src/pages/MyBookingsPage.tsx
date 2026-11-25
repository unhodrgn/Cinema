import { useRef, useState } from "react";
import { BookingSummary } from "../features/booking/BookingSummary";
import { RequireUser } from "../components/common/Navbar";
import { useResource } from "../hooks/useResource";
import { errorMessage, post } from "../services/apiClient";
import type { Booking } from "../types/cinema";

function History() {
  const { data, error, reload } = useResource<{ bookings: Booking[] }>(
    "/api/bookings",
  );
  const [message, setMessage] = useState("");
  const [cancellingId, setCancellingId] = useState<number | null>(null);
  const inFlight = useRef(false);
  async function cancel(id: number) {
    if (
      inFlight.current ||
      !confirm("Are you sure you want to cancel this booking?")
    )
      return;
    inFlight.current = true;
    setCancellingId(id);
    setMessage("");
    try {
      await post("/api/bookings/" + id + "/cancel");
      reload();
    } catch (e) {
      setMessage(errorMessage(e));
    } finally {
      inFlight.current = false;
      setCancellingId(null);
    }
  }
  return (
    <>
      <h1>My Bookings</h1>
      {(error || message) && (
        <p
          className={error ? "message message-error" : "message message-info"}
          role={error ? "alert" : "status"}
        >
          {error || message}
        </p>
      )}
      {!data && !error && <p role="status">Loading bookings…</p>}
      {data && !data.bookings.length && (
        <p className="card muted">
          You have no bookings yet.{" "}
          <a href="/screenings.html">Browse screening schedule</a>
        </p>
      )}
      {data?.bookings.map((b) => (
        <BookingSummary key={b.booking_id} booking={b}>
          <div className="booking-actions">
            <a
              className="button button-secondary"
              href={"/booking.html?id=" + b.booking_id}
            >
              View Details
            </a>
            {b.status === "BOOKED" && b.payment_status === "UNPAID" && (
              <a className="button" href={"/booking.html?id=" + b.booking_id}>
                Pay Now
              </a>
            )}
            {b.status === "BOOKED" && Date.parse(b.starts_at) > Date.now() && (
              <button
                className="button button-danger"
                disabled={cancellingId !== null}
                aria-busy={cancellingId === b.booking_id || undefined}
                onClick={() => cancel(b.booking_id)}
              >
                {cancellingId === b.booking_id ? "Cancelling…" : "Cancel"}
              </button>
            )}
          </div>
        </BookingSummary>
      ))}
    </>
  );
}
export function MyBookingsPage() {
  return (
    <RequireUser>
      <History />
    </RequireUser>
  );
}
