import { useEffect, useRef, useState } from "react";
import { RequireUser } from "../components/common/Navbar";
import { BookingSummary } from "../features/booking/BookingSummary";
import { BookingSteps } from "../features/booking/BookingSteps";
import { CountdownTimer } from "../features/booking/CountdownTimer";
import { TicketSuccessPage } from "./TicketSuccessPage";
import { confirmExpiry } from "../../js/deadline.js";
import { isIdText } from "../../js/format.js";
import { errorMessage, get, post } from "../services/apiClient";
import type { Booking } from "../types/cinema";

const expiredMessage =
  "The booking has expired. Your seats have been released.";

function Checkout() {
  const id = new URLSearchParams(location.search).get("id");
  const path = "/api/bookings/" + id;
  const [booking, setBooking] = useState<Booking>();
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    if (isIdText(id))
      get<{ booking: Booking }>(path)
        .then((data) => setBooking(data.booking))
        .catch((e) => setError(errorMessage(e)));
  }, [path]);
  async function elapsed() {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    try {
      const result = await confirmExpiry({
        reload: async () => (await get<{ booking: Booking }>(path)).booking,
        wait: (ms: number) => new Promise((resolve) => setTimeout(resolve, ms)),
      });
      setBooking(result.booking);
      if (result.booking?.status === "EXPIRED") setError(expiredMessage);
      setNotice(result.stillOpen ? "The server still accepts payment." : "");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  async function change(action: "pay" | "cancel") {
    if (
      inFlight.current ||
      (action === "cancel" &&
        !confirm("Are you sure you want to cancel this booking?"))
    )
      return;
    inFlight.current = true;
    setBusy(true);
    setNotice("");
    setError("");
    try {
      const data = await post<{ booking: Booking; outcome: string }>(
        path + "/" + action,
      );
      setBooking(data.booking);
      if (data.outcome === "EXPIRED") setError(expiredMessage);
      if (data.outcome === "CANCELLED") setNotice("Booking cancelled.");
    } catch (e) {
      setError(errorMessage(e));
      // The write may have committed before the connection failed.
      try {
        const data = await get<{ booking: Booking }>(path);
        setBooking(data.booking);
        if (data.booking.status === "EXPIRED") setError(expiredMessage);
      } catch {
        // Keep the original request error and allow a retry.
      }
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  const problem = isIdText(id) ? error : "Invalid or missing booking ID.";
  const paid = booking?.payment_status === "PAID";
  return (
    <div className="narrow">
      <BookingSteps current={paid ? "Payment" : "Booking"} />
      <h1>Booking Details</h1>
      {problem && (
        <p className="message message-error" role="alert">
          {problem}
        </p>
      )}
      {notice && (
        <p className="message message-info" role="status">
          {notice}
        </p>
      )}
      {!booking && !problem && <p role="status">Loading booking…</p>}
      {booking && (
        <>
          <BookingSummary booking={booking} />
          {booking.status === "BOOKED" && booking.payment_status === "PAID" && (
            <TicketSuccessPage booking={booking} />
          )}
          {booking.status === "BOOKED" &&
            booking.payment_status === "UNPAID" && (
              <div className="message message-info">
                <p>
                  Complete simulated payment before the deadline to confirm your
                  seats.
                </p>
                <CountdownTimer
                  expiresAt={booking.expires_at}
                  onElapsed={elapsed}
                />
                <button
                  className="button"
                  disabled={busy}
                  onClick={() => change("pay")}
                >
                  Pay Now
                </button>
              </div>
            )}
        </>
      )}
      <div className="booking-actions">
        {booking?.status === "BOOKED" &&
          Date.parse(booking.starts_at) > Date.now() && (
            <button
              className="button button-danger"
              disabled={busy}
              onClick={() => change("cancel")}
            >
              Cancel Booking
            </button>
          )}
        <a className="button button-secondary" href="/bookings.html">
          My Bookings
        </a>
      </div>
    </div>
  );
}
export function CheckoutPage() {
  return (
    <RequireUser>
      <Checkout />
    </RequireUser>
  );
}
