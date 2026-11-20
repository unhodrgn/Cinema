// Booking detail, simulated payment, and cancellation page.
// All values are rendered with text nodes (no innerHTML).

import { getApi } from "../api.js";
import { getAuth, loginUrl } from "../auth.js";
import { formatMoney, formatTimeRange } from "../format.js";
import { initNav } from "../nav.js";
import { seatLabel } from "../seats.js";
import { clear, el, showMessage } from "../ui.js";

async function main() {
  await initNav(document.getElementById("site-nav"));

  const auth = getAuth();
  let user = null;
  try {
    user = await auth.currentUser();
  } catch {
    user = null;
  }

  const messageBox = document.getElementById("message");
  const card = document.getElementById("booking-card");
  const movieTitle = document.getElementById("movie-title");
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

  let timerInterval = null;

  function stopTimer() {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
  }

  function startCountdown(expiresAtIso) {
    stopTimer();
    const expiresMs = Date.parse(expiresAtIso);
    if (Number.isNaN(expiresMs)) return;

    function update() {
      const remainingMs = expiresMs - Date.now();
      if (remainingMs <= 0) {
        countdownTimer.textContent = "Time elapsed! This booking will expire.";
        stopTimer();
        return;
      }
      const totalSec = Math.floor(remainingMs / 1000);
      const min = Math.floor(totalSec / 60);
      const sec = totalSec % 60;
      countdownTimer.textContent = `Time remaining: ${min}m ${sec < 10 ? "0" : ""}${sec}s`;
    }

    update();
    timerInterval = setInterval(update, 1000);
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
    bookingIdEl.textContent = String(b.booking_id);
    roomNameEl.textContent = b.room_name;
    screeningTimeEl.textContent = formatTimeRange(b.starts_at, b.ends_at);
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
    payButton.disabled = true;
    clear(messageBox);
    try {
      const response = await getApi().post(`/api/bookings/${bookingId}/pay`, {});
      if (response.outcome === "PAID") {
        showMessage(messageBox, "success", "Payment successful! Your booking is fully confirmed.");
      } else if (response.outcome === "EXPIRED") {
        showMessage(messageBox, "error", "Payment window has elapsed. The booking has expired and seats are released.");
      }
      render(response.booking);
    } catch (err) {
      showMessage(messageBox, "error", err.message || "Payment failed.");
      await loadBooking();
    } finally {
      payButton.disabled = false;
    }
  });

  cancelButton.addEventListener("click", async () => {
    if (!globalThis.confirm("Are you sure you want to cancel this booking? Released seats will be made available for others.")) {
      return;
    }
    cancelButton.disabled = true;
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
      cancelButton.disabled = false;
    }
  });

  await loadBooking();
}

globalThis.addEventListener("DOMContentLoaded", main);
