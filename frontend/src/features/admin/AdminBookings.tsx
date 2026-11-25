import { useState, type FormEvent } from "react";
import {
  readFilters,
  bookingTimeline,
  paymentKind,
  seatsText,
  statusKind,
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
      {error && (
        <p className="message message-error" role="alert">
          {error}
        </p>
      )}
      <section className="card">
        <h2>Filter</h2>
        <form
          className="toolbar toolbar-flush"
          onSubmit={apply}
          onReset={() => {
            setProblem("");
            setQuery("");
          }}
        >
          <label htmlFor="status-filter">Status</label>
          <select id="status-filter" name="status">
            <option value="">All</option>
            {["BOOKED", "CANCELLED", "EXPIRED"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <label htmlFor="screening-filter">Screening ID</label>
          <input
            id="screening-filter"
            name="screening_id"
            className="input-id"
            inputMode="numeric"
          />
          <label htmlFor="customer-filter">Customer ID</label>
          <input
            id="customer-filter"
            name="user_id"
            className="input-id"
            inputMode="numeric"
          />
          <button className="button">Apply filters</button>
          <button className="button button-secondary" type="reset">
            Clear
          </button>
        </form>
        {problem && (
          <p className="field-error" role="alert">
            {problem}
          </p>
        )}
      </section>
      {!data && !error && <p role="status">Loading bookings…</p>}
      {data && (
        <section className="section-gap">
          <div className="section-head">
            <h2>Bookings</h2>
            <p className="muted" aria-live="polite">
              {data.bookings.length} booking
              {data.bookings.length === 1 ? "" : "s"}
            </p>
          </div>
          <div className="card card-flush">
            {data.bookings.length ? (
              <div className="table-wrap">
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
                        <td className="cell-strong">
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
                          <div className="badges">
                            <span
                              className={"badge badge-" + statusKind(b.status)}
                            >
                              {b.status}
                            </span>
                            <span
                              className={
                                "badge badge-" + paymentKind(b.payment_status)
                              }
                            >
                              {b.payment_status}
                            </span>
                          </div>
                        </td>
                        <td>{formatDateTime(b.booked_at)}</td>
                        <td>{bookingTimeline(b)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="muted empty-note">No bookings found.</p>
            )}
          </div>
        </section>
      )}
    </>
  );
}
