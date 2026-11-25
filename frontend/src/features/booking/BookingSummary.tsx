import type { ReactNode } from "react";
import {
  formatDateTime,
  formatDateTimeRange,
  formatMoney,
} from "../../../js/format.js";
import { seatLabel } from "../../../js/seats.js";
import { Poster } from "../movies/MovieCard";
import type { Booking } from "../../types/cinema";

export function BookingSummary({
  booking: b,
  children,
}: {
  booking: Booking;
  children?: ReactNode;
}) {
  return (
    <article className="card booking-detail">
      <Poster title={b.title} url={b.poster_url} size="sm" />
      <div className="booking-detail-body">
        <div className="booking-header">
          <h2>{b.title}</h2>
          <div className="badges">
            <span
              className={
                "badge badge-" +
                (b.status === "BOOKED"
                  ? "ok"
                  : b.status === "EXPIRED"
                    ? "error"
                    : "neutral")
              }
            >
              {b.status}
            </span>
            <span
              className={
                "badge badge-" + (b.payment_status === "PAID" ? "ok" : "wait")
              }
            >
              {b.payment_status}
            </span>
          </div>
        </div>
        <dl className="facts">
          <dt>Booking ID</dt>
          <dd>{b.booking_id}</dd>
          <dt>Room</dt>
          <dd>{b.room_name}</dd>
          <dt>Screening</dt>
          <dd>{formatDateTimeRange(b.starts_at, b.ends_at)}</dd>
          <dt>Seats</dt>
          <dd>{b.seats.map(seatLabel).join(", ") || "Released"}</dd>
          <dt>Total Amount</dt>
          <dd>
            <strong>{formatMoney(b.total_amount)}</strong>
          </dd>
          <dt>Booked At</dt>
          <dd>{formatDateTime(b.booked_at)}</dd>
          {b.status === "BOOKED" && b.payment_status === "UNPAID" && (
            <>
              <dt>Payment Deadline</dt>
              <dd>{formatDateTime(b.expires_at)}</dd>
            </>
          )}
        </dl>
        {children}
      </div>
    </article>
  );
}
