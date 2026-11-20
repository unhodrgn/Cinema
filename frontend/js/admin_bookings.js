// Pure helpers for the admin booking list (T8, B03 A-03): filters, status badges and the table
// columns. No network and no page code here, so they can be tested without a browser.
// All text reaches the page through ui.js / admin.js (text nodes only).

import { badge } from "./admin.js";
import { formatDateTime, formatMoney, isIdText } from "./format.js";
import { seatLabel } from "./seats.js";
import { el } from "./ui.js";

export const BOOKING_STATUSES = ["BOOKED", "CANCELLED", "EXPIRED"];

/** Badge colour for a booking status (same mapping as the customer pages). */
export function statusKind(status) {
  if (status === "BOOKED") return "ok";
  if (status === "EXPIRED") return "error";
  return "neutral";
}

/** Badge colour for a payment status. */
export function paymentKind(paymentStatus) {
  return paymentStatus === "PAID" ? "ok" : "wait";
}

/** "A1, A2" for a booking that still holds seats; "Released" once the seats were given back. */
export function seatsText(booking) {
  if (!booking) return "";
  const seats = Array.isArray(booking?.seats) ? booking.seats : [];
  if (seats.length > 0) return seats.map(seatLabel).filter(Boolean).join(", ");
  return booking?.status === "BOOKED" ? "-" : "Released";
}

/** One short line saying what happened last to the booking (times as the API wrote them). */
export function bookingTimeline(booking) {
  if (!booking) return "";
  if (booking.status === "CANCELLED") return `Cancelled ${formatDateTime(booking.cancelled_at)}`.trim();
  if (booking.status === "EXPIRED") return `Expired (window ended ${formatDateTime(booking.expires_at)})`;
  if (booking.payment_status === "PAID") return `Paid ${formatDateTime(booking.paid_at)}`.trim();
  return `Pay by ${formatDateTime(booking.expires_at)}`;
}

/**
 * Check the raw filter values from the form. Returns `{ query, problems }`: `query` holds only
 * the filters that were filled in (ready for `api.get(path, { query })`), `problems` maps a
 * field name to a message. The server validates again; this only gives quicker feedback.
 */
export function readFilters({ status = "", screeningId = "", userId = "" } = {}) {
  const query = {};
  const problems = {};
  const statusText = String(status).trim().toUpperCase();
  if (statusText) {
    if (BOOKING_STATUSES.includes(statusText)) query.status = statusText;
    else problems.status = "Choose BOOKED, CANCELLED or EXPIRED.";
  }
  for (const [name, raw] of [["screening_id", screeningId], ["user_id", userId]]) {
    const text = String(raw).trim();
    if (!text) continue;
    if (isIdText(text)) query[name] = text;
    else problems[name] = "Must be a positive whole number.";
  }
  return { query, problems };
}

/** The columns of the admin booking table, for `dataTable` in admin.js. */
export function bookingColumns() {
  return [
    { header: "Booking", cell: (b) => `#${b.booking_id}` },
    { header: "Customer", className: "cell-strong", cell: (b) => `${b.username} (#${b.user_id})` },
    { header: "Movie", cell: (b) => b.title },
    {
      header: "Screening",
      cell: (b) => `#${b.showtime_id} · ${b.room_name} · ${formatDateTime(b.starts_at)}`,
    },
    { header: "Seats", cell: (b) => seatsText(b) },
    { header: "Total", cell: (b) => formatMoney(b.total_amount) },
    {
      header: "Status",
      cell: (b) =>
        el("div", { className: "badges" }, badge(statusKind(b.status), b.status), badge(paymentKind(b.payment_status), b.payment_status)),
    },
    { header: "Booked", cell: (b) => formatDateTime(b.booked_at) },
    { header: "Last event", cell: (b) => bookingTimeline(b) },
  ];
}
