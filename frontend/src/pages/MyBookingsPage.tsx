import { useState } from "react";
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
  async function cancel(id: number) {
    if (!confirm("Are you sure you want to cancel this booking?")) return;
    try {
      await post("/api/bookings/" + id + "/cancel");
      reload();
    } catch (e) {
      setMessage(errorMessage(e));
    }
  }
  return (
    <>
      <h1>My Bookings</h1>
      <p role="status">{error || message}</p>
      {data && !data.bookings.length && (
        <p>
          You have no bookings yet.{" "}
          <a href="/screenings.html">Browse screening schedule</a>
        </p>
      )}
      {data?.bookings.map((b) => (
        <section key={b.booking_id}>
          <BookingSummary booking={b} />
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
                onClick={() => cancel(b.booking_id)}
              >
                Cancel
              </button>
            )}
          </div>
        </section>
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
