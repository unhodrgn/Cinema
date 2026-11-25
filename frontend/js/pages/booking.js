// Booking detail, simulated payment, and cancellation page.
// All values are rendered with text nodes (no innerHTML).

import { getApi } from "../api.js";
import { getAuth, loginUrl, pageUser } from "../auth.js";
import { confirmExpiry, createCountdown } from "../deadline.js";
import { formatDateTimeRange, formatMoney } from "../format.js";
import { initNav } from "../nav.js";
import { posterFrame } from "../poster.js";
import { seatLabel } from "../seats.js";
import { clear, el, showMessage } from "../ui.js";

async function main() {
  await initNav(document.getElementById("site-nav"));

  const messageBox = document.getElementById("message");
  const { user, failed } = await pageUser(getAuth(), messageBox);
  if (failed) return;

  const card = document.getElementById("booking-card");
  const movieTitle = document.getElementById("movie-title");
  const posterBox = document.getElementById("booking-poster");
  const badgesBox = document.getElementById("badges");
  const bookingIdEl = document.getElementById("booking-id");
  const roomNameEl = document.getElementById("room-name");
  const screeningTimeEl = document.getElementById("screening-time");
  const seatListEl = document.getElementById("seat-list");
  const totalAmountEl = document.getElementById("total-amount");
  const bookedAtEl = document.getElementById("booked-at");
  const deadlineLabel = document.getElementById("payment-deadline-label");
  const deadlineValue = document.getElementById("payment-deadline-value");
  const paymentBox = document.getElementById("payment-box");
  const countdownTimer = document.getElementById("countdown-timer");
  const payButton = document.getElementById("pay-button");
  const cancelButton = document.getElementById("cancel-button");

  const params = new URLSearchParams(globalThis.location.search);
  const bookingId = params.get("id");

  if (!bookingId || !/^[1-9]\d*$/.test(bookingId)) {
    showMessage(messageBox, "error", "Invalid or missing booking ID.");
    return;
  }

  if (!user) {
    globalThis.location.assign(loginUrl(`/booking.html?id=${bookingId}`));
    return;
  }

  let countdown = null;
  let deadlineChecked = false; // the post-deadline check ran once; do not repeat it forever
  let isActionInFlight = false;

  function stopTimer() {
    if (countdown) {
      countdown.stop();
      countdown = null;
    }
  }

  const EXPIRED_TEXT = "Payment window has elapsed. The booking has expired and seats are released.";

  /** The countdown reached zero: the server decides, so ask it again and show the answer. */
  async function onDeadlineReached() {
    payButton.disabled = true;
    if (deadlineChecked) {
      countdownTimer.textContent = "Time elapsed. Press Pay Now to check the booking status.";
      if (!isActionInFlight) payButton.disabled = false;
      return;
    }
    deadlineChecked = true;
    countdownTimer.textContent = "Time elapsed. Checking the booking status…";
    const { booking, stillOpen } = await confirmExpiry({
      reload: async () => {
        try {
          return (await getApi().get(`/api/bookings/${bookingId}`)).booking;
        } catch {
          return null;
        }
      },
      wait: (ms) => new Promise((resolve) => globalThis.setTimeout(resolve, ms)),
    });
    if (!booking) {
      countdownTimer.textContent = "Time elapsed. The booking status could not be loaded; reload the page.";
      if (!isActionInFlight) payButton.disabled = false;
      return;
    }
    render(booking);
    if (booking.status === "EXPIRED") {
      showMessage(messageBox, "error", EXPIRED_TEXT);
    } else if (stillOpen && !isActionInFlight) {
      payButton.disabled = false; // the server still allows payment: let the user try
    }
  }

  function startCountdown(expiresAtIso) {
    stopTimer();
    payButton.disabled = isActionInFlight;
    countdown = createCountdown({
      expiresAtIso,
      onTick: (text) => {
        countdownTimer.textContent = text;
      },
      onElapsed: onDeadlineReached,
    });
  }

  async function loadBooking() {
    clear(messageBox);
    try {
      const data = await getApi().get(`/api/bookings/${bookingId}`);
      render(data.booking);
    } catch (err) {
      card.hidden = true;
      showMessage(messageBox, "error", err.message || "Failed to load booking.");
    }
  }

  function render(b) {
    card.hidden = false;
    movieTitle.textContent = b.title;
    clear(posterBox);
    posterBox.append(posterFrame(b.title, b.poster_url, { size: "sm" }));
    const paid = b.payment_status === "PAID"; // steps: Seats (done) -> Booking -> Payment
    document.getElementById("step-booking").classList.toggle("step-current", !paid);
    document.getElementById("step-payment").classList.toggle("step-current", paid);
    bookingIdEl.textContent = String(b.booking_id);
    roomNameEl.textContent = b.room_name;
    screeningTimeEl.textContent = formatDateTimeRange(b.starts_at, b.ends_at);
    totalAmountEl.textContent = formatMoney(b.total_amount);
    bookedAtEl.textContent = b.booked_at ? b.booked_at.slice(0, 19).replace("T", " ") : "-";

    // Badges
    clear(badgesBox);
    const statusClass = b.status === "BOOKED" ? "badge-ok" : b.status === "EXPIRED" ? "badge-error" : "badge-neutral";
    badgesBox.append(el("span", { className: `badge ${statusClass}`, text: b.status }));

    const payClass = b.payment_status === "PAID" ? "badge-ok" : "badge-wait";
    badgesBox.append(el("span", { className: `badge ${payClass}`, text: b.payment_status }));

    // Seats
    if (b.status === "BOOKED" && b.seats && b.seats.length > 0) {
      const seatNames = b.seats.map(seatLabel).join(", ");
      seatListEl.textContent = seatNames;
    } else {
      seatListEl.textContent = "Seats released";
    }

    // Payment Box & Deadlines
    stopTimer();
    if (b.status === "BOOKED" && b.payment_status === "UNPAID") {
      deadlineLabel.hidden = false;
      deadlineValue.hidden = false;
      deadlineValue.textContent = b.expires_at ? b.expires_at.slice(0, 19).replace("T", " ") : "-";
      paymentBox.hidden = false;
      startCountdown(b.expires_at);
    } else {
      deadlineLabel.hidden = true;
      deadlineValue.hidden = true;
      paymentBox.hidden = true;
    }

    // Cancel Button
    const screeningStarted = Date.parse(b.starts_at) <= Date.now();
    if (b.status === "BOOKED" && !screeningStarted) {
      cancelButton.hidden = false;
    } else {
      cancelButton.hidden = true;
    }
  }

  payButton.addEventListener("click", async () => {
    if (isActionInFlight) return;
    isActionInFlight = true;
    payButton.disabled = true;
    cancelButton.disabled = true;
    payButton.setAttribute("aria-busy", "true");
    payButton.textContent = "Processing…";
    clear(messageBox);
    try {
      const response = await getApi().post(`/api/bookings/${bookingId}/pay`, {});
      if (response.outcome === "PAID") {
        showMessage(messageBox, "success", "Payment successful! Your booking is fully confirmed.");
      } else if (response.outcome === "EXPIRED") {
        showMessage(messageBox, "error", EXPIRED_TEXT);
      }
      render(response.booking);
    } catch (err) {
      showMessage(messageBox, "error", err.message || "Payment failed.");
      await loadBooking();
    } finally {
      isActionInFlight = false;
      payButton.removeAttribute("aria-busy");
      payButton.textContent = "Pay Now (Simulated)";
      payButton.disabled = false;
      cancelButton.disabled = false;
    }
  });

  cancelButton.addEventListener("click", async () => {
    if (isActionInFlight) return;
    if (!globalThis.confirm("Are you sure you want to cancel this booking? Released seats will be made available for others.")) {
      return;
    }
    isActionInFlight = true;
    cancelButton.disabled = true;
    payButton.disabled = true;
    cancelButton.setAttribute("aria-busy", "true");
    cancelButton.textContent = "Cancelling…";
    clear(messageBox);
    try {
      const response = await getApi().post(`/api/bookings/${bookingId}/cancel`, {});
      if (response.outcome === "CANCELLED") {
        showMessage(messageBox, "success", "Booking has been cancelled. Seats have been released.");
      } else if (response.outcome === "EXPIRED") {
        showMessage(messageBox, "info", "Payment deadline elapsed; booking was expired and seats released.");
      }
      render(response.booking);
    } catch (err) {
      showMessage(messageBox, "error", err.message || "Cancellation failed.");
      await loadBooking();
    } finally {
      isActionInFlight = false;
      cancelButton.removeAttribute("aria-busy");
      cancelButton.textContent = "Cancel Booking";
      cancelButton.disabled = false;
      payButton.disabled = false;
    }
  });

  await loadBooking();
}

globalThis.addEventListener("DOMContentLoaded", main);
