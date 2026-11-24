import { useState, type FormEvent } from "react";
import {
  readFilters,
  bookingTimeline,
  seatsText,
} from "../../../js/admin_bookings.js";
import { formatDateTime, formatMoney } from "../../../js/format.js";
import { useResource } from "../../hooks/useResource";
import type { Booking } from "../../types/cinema";

export function AdminBookings() {
  const [query, setQuery] = useState("");
  const [problem, setProblem] = useState("");
  const { data, error } = useResource<{ bookings: Booking[] }>(
    "/api/admin/bookings?" + query,
  );
  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const filters = readFilters({
      status: String(form.get("status")),
      screeningId: String(form.get("screening_id")),
      userId: String(form.get("user_id")),
    });
    setProblem(Object.values(filters.problems).join(" "));
    if (!Object.keys(filters.problems).length)
      setQuery(new URLSearchParams(Object.entries(filters.query)).toString());
  }
  return (
    <>
      <h1>All Bookings</h1>
      <form
        className="card form"
        onSubmit={apply}
        onReset={() => {
          setProblem("");
          setQuery("");
        }}
      >
        <div className="field">
          <label htmlFor="status-filter">Status</label>
          <select id="status-filter" name="status">
            <option value="">All</option>
            {["BOOKED", "CANCELLED", "EXPIRED"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="screening-filter">Screening ID</label>
          <input
            id="screening-filter"
            name="screening_id"
            inputMode="numeric"
          />
        </div>
        <div className="field">
          <label htmlFor="customer-filter">Customer ID</label>
          <input id="customer-filter" name="user_id" inputMode="numeric" />
        </div>
        <div className="form-actions">
          <button className="button">Apply filters</button>{" "}
          <button className="button button-secondary" type="reset">
            Clear
          </button>
        </div>
      </form>
      <p role="status">{problem || error}</p>
      {data &&
        (data.bookings.length ? (
          <div className="table-wrap section-gap">
            <table className="data-table">
              <thead>
                <tr>
                  {[
                    "Booking",
                    "Customer",
                    "Movie",
                    "Screening",
                    "Seats",
                    "Total",
                    "Status",
                    "Booked",
                    "Last event",
                  ].map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.bookings.map((b) => (
                  <tr key={b.booking_id}>
                    <td>#{b.booking_id}</td>
                    <td>
                      {b.username} (#{b.user_id})
                    </td>
                    <td>{b.title}</td>
                    <td>
                      #{b.showtime_id} · {b.room_name} ·{" "}
                      {formatDateTime(b.starts_at)}
                    </td>
                    <td>{seatsText(b)}</td>
                    <td>{formatMoney(b.total_amount)}</td>
                    <td>
                      {b.status} · {b.payment_status}
                    </td>
                    <td>{formatDateTime(b.booked_at)}</td>
                    <td>{bookingTimeline(b)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="section-gap">No bookings found.</p>
        ))}
    </>
  );
}
