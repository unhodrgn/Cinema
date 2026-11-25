// Customer booking history page (T6, B03 C-08).
// Displays bookings with status badges, seats (for BOOKED only), and payment/cancellation actions.

import { getApi } from "../api.js";
import { getAuth, loginUrl, pageUser } from "../auth.js";
import { formatDateTimeRange, formatMoney } from "../format.js";
import { initNav } from "../nav.js";
import { posterFrame } from "../poster.js";
import { seatLabel } from "../seats.js";
import { clear, el, showMessage } from "../ui.js";

async function main() {
  await initNav(document.getElementById("site-nav"));

  const messageBox = document.getElementById("message");
  const container = document.getElementById("bookings-container");
  const { user, failed } = await pageUser(getAuth(), messageBox);
  if (failed) return;

  if (!user) {
    globalThis.location.assign(loginUrl("/bookings.html"));
    return;
  }

  if (user.role !== "CUSTOMER") {
    showMessage(messageBox, "error", "Only customer accounts can view personal booking history.");
    return;
  }

  let isCancelling = false;

  async function loadBookings() {
    clear(messageBox);
    clear(container);

    try {
      const data = await getApi().get("/api/bookings");
      const list = data.bookings || [];

      if (list.length === 0) {
        container.append(
          el(
            "p",
            { className: "card muted" },
            "You have no bookings yet. ",
            el("a", { attrs: { href: "/screenings.html" }, text: "Browse screening schedule" }),
          ),
        );
        return;
      }

      for (const b of list) {
        container.append(renderBookingCard(b));
      }
    } catch (err) {
      showMessage(messageBox, "error", err.message || "Failed to load booking history.");
    }
  }

  function renderBookingCard(b) {
    const card = el("article", { className: "card booking-history-card" });

    // Header: Movie title & badges
    const header = el("div", { className: "booking-card-header" });
    header.append(el("h2", { text: b.title }));

    const badges = el("div", { className: "badges" });
    const statusClass = b.status === "BOOKED" ? "badge-ok" : b.status === "EXPIRED" ? "badge-error" : "badge-neutral";
    badges.append(el("span", { className: `badge ${statusClass}`, text: b.status }));

    const payClass = b.payment_status === "PAID" ? "badge-ok" : "badge-wait";
    badges.append(el("span", { className: `badge ${payClass}`, text: b.payment_status }));
    header.append(badges);

    // Facts list
    const facts = el("dl", { className: "facts" });
    facts.append(
      el("dt", { text: "Booking ID" }),
      el("dd", { text: String(b.booking_id) }),
      el("dt", { text: "Screening" }),
      el("dd", { text: `${formatDateTimeRange(b.starts_at, b.ends_at)} · ${b.room_name}` }),
      el("dt", { text: "Total Amount" }),
      el("dd", { text: formatMoney(b.total_amount) }),
      el("dt", { text: "Booked At" }),
      el("dd", { text: b.booked_at ? b.booked_at.slice(0, 19).replace("T", " ") : "-" }),
    );

    if (b.status === "BOOKED" && b.seats && b.seats.length > 0) {
      facts.append(
        el("dt", { text: "Seats" }),
        el("dd", { text: b.seats.map(seatLabel).join(", ") }),
      );
    } else {
      facts.append(
        el("dt", { text: "Seats" }),
        el("dd", { className: "muted", text: "Released" }),
      );
    }

    const body = el("div", { className: "booking-card-body" }, header, facts);
    card.append(posterFrame(b.title, b.poster_url, { size: "sm" }), body);

    // Actions
    const actions = el("div", { className: "booking-actions" });
    actions.append(
      el("a", {
        className: "button button-secondary",
        attrs: { href: `/booking.html?id=${b.booking_id}` },
        text: "View Details",
      }),
    );

    if (b.status === "BOOKED" && b.payment_status === "UNPAID") {
      actions.append(
        el("a", {
          className: "button",
          attrs: { href: `/booking.html?id=${b.booking_id}` },
          text: "Pay Now",
        }),
      );
    }

    const screeningStarted = Date.parse(b.starts_at) <= Date.now();
    if (b.status === "BOOKED" && !screeningStarted) {
      const cancelBtn = el("button", {
        className: "button button-danger",
        attrs: { type: "button" },
        text: "Cancel",
      });
      cancelBtn.addEventListener("click", async () => {
        if (isCancelling) return;
        if (!globalThis.confirm("Are you sure you want to cancel this booking?")) return;
        isCancelling = true;
        cancelBtn.disabled = true;
        cancelBtn.setAttribute("aria-busy", "true");
        cancelBtn.textContent = "Cancelling…";
        try {
          await getApi().post(`/api/bookings/${b.booking_id}/cancel`, {});
          await loadBookings();
        } catch (err) {
          showMessage(messageBox, "error", err.message || "Failed to cancel booking.");
          cancelBtn.disabled = false;
          cancelBtn.removeAttribute("aria-busy");
          cancelBtn.textContent = "Cancel";
        } finally {
          isCancelling = false;
        }
      });
      actions.append(cancelBtn);
    }

    body.append(actions);
    return card;
  }

  await loadBookings();
}

globalThis.addEventListener("DOMContentLoaded", main);
