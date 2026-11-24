// Seat picker page: loads screening and seat availability, enables provisional seat selection,
// preserves selection on login redirect, and proceeds to booking creation when authenticated.

import { getApi } from "../api.js";
import { getAuth, loginUrl, pageUser } from "../auth.js";
import { formatMoney, formatTimeRange } from "../format.js";
import { initNav } from "../nav.js";
import { posterFrame } from "../poster.js";
import {
  calculateTotal,
  dropUnavailable,
  formatSelectedSeats,
  groupSeatsByRow,
  parseSelectedSeats,
  seatLabel,
  takenSeatsMessage,
} from "../seats.js";
import { clear, el, showMessage } from "../ui.js";

async function main() {
  await initNav(document.getElementById("site-nav"));

  const messageBox = document.getElementById("message");
  const infoContainer = document.getElementById("screening-info");
  const pickerCard = document.getElementById("seat-picker-card");
  const gridContainer = document.getElementById("seat-grid");
  const selectedListSpan = document.getElementById("selected-list");
  const totalPriceSpan = document.getElementById("total-price");
  const ticketLine = document.getElementById("ticket-line");
  const bookButton = document.getElementById("book-button");

  const params = new URLSearchParams(globalThis.location.search);
  const screeningId = params.get("screening_id");

  if (!screeningId || !/^[1-9]\d*$/.test(screeningId)) {
    showMessage(messageBox, "error", "Invalid or missing screening ID.");
    return;
  }

  const preselected = new Set(parseSelectedSeats(params.get("selected")));
  const selectedSeats = new Set(); // holds numeric seat_id

  let screeningData = null;
  let allSeats = [];
  const seatMap = new Map(); // seat_id -> seat object

  /** Reload the seat map. Seats of the selection that are no longer free are dropped from it.
   *  Returns `{ ok, removed }`: whether the map was loaded and the labels that were dropped. */
  async function loadData() {
    clear(messageBox);
    try {
      const data = await getApi().get(`/api/screenings/${screeningId}/seats`);
      screeningData = data.screening;
      allSeats = data.seats || [];
      seatMap.clear();
      for (const s of allSeats) {
        seatMap.set(s.seat_id, s);
      }
      const removed = dropUnavailable(selectedSeats, allSeats);
      renderScreeningInfo();
      renderSeatGrid();
      updateSummary();
      pickerCard.hidden = false;
      return { ok: true, removed };
    } catch (err) {
      pickerCard.hidden = true;
      showMessage(messageBox, "error", err.message || "Failed to load seats.");
      return { ok: false, removed: [] };
    }
  }

  function renderScreeningInfo() {
    clear(infoContainer);
    if (!screeningData) return;

    const titleEl = el("h2", { text: screeningData.title });
    const poster = posterFrame(screeningData.title, screeningData.poster_url, { size: "sm" });
    const timeEl = el("p", {
      text: `${formatTimeRange(screeningData.starts_at, screeningData.ends_at)} · ${screeningData.room_name}`,
    });
    const priceEl = el("p", {
      className: "muted",
      text: `Price per seat: ${formatMoney(screeningData.ticket_price)}`,
    });
    const body = el("div", { className: "screening-info-body" }, titleEl, timeEl, priceEl);
    infoContainer.append(poster, body);

    if (screeningData.has_started) {
      body.append(
        el("div", {
          className: "badge badge-neutral",
          text: "This screening has already started and cannot be booked.",
        }),
      );
      bookButton.disabled = true;
    }
  }

  function renderSeatGrid() {
    clear(gridContainer);
    const rows = groupSeatsByRow(allSeats);

    // Initialise preselected seats (only if available)
    for (const id of preselected) {
      const s = seatMap.get(id);
      if (s && s.is_available) {
        selectedSeats.add(id);
      }
    }
    preselected.clear();

    for (const [rowLetter, seatsInRow] of rows.entries()) {
      const rowEl = el("div", { className: "seat-row" });
      rowEl.append(el("span", { className: "seat-row-label", attrs: { "aria-hidden": "true" }, text: rowLetter }));

      for (const seat of seatsInRow) {
        if (seat.seat_number === 6) rowEl.append(el("span", { className: "seat-aisle", attrs: { "aria-hidden": "true" } }));
        const isOccupied = !seat.is_available;
        const isSelected = selectedSeats.has(seat.seat_id);

        let btnClass = "seat-btn";
        if (isSelected) btnClass += " selected";
        if (isOccupied) btnClass += " occupied";

        const btn = el("button", {
          className: btnClass,
          attrs: {
            type: "button",
            "aria-label": `Seat ${seatLabel(seat)}${isOccupied ? " (Occupied)" : ""}`,
            title: `Seat ${seatLabel(seat)}`,
            disabled: isOccupied || screeningData.has_started,
          },
          text: String(seat.seat_number),
          on: {
            click: () => {
              if (selectedSeats.has(seat.seat_id)) {
                selectedSeats.delete(seat.seat_id);
                btn.classList.remove("selected");
              } else {
                selectedSeats.add(seat.seat_id);
                btn.classList.add("selected");
              }
              updateSummary();
            },
          },
        });
        rowEl.append(btn);
      }
      rowEl.append(el("span", { className: "seat-row-label", attrs: { "aria-hidden": "true" }, text: rowLetter }));
      gridContainer.append(rowEl);
    }
  }

  function updateSummary() {
    if (selectedSeats.size === 0) {
      selectedListSpan.textContent = "None";
      totalPriceSpan.textContent = formatMoney("0");
      ticketLine.textContent = `0 × ${formatMoney(screeningData ? screeningData.ticket_price : "0")}`;
      bookButton.disabled = true;
      return;
    }

    const sortedLabels = Array.from(selectedSeats)
      .map((id) => seatMap.get(id))
      .filter(Boolean)
      .sort((a, b) => a.seat_row.localeCompare(b.seat_row) || a.seat_number - b.seat_number)
      .map(seatLabel);

    selectedListSpan.textContent = sortedLabels.join(", ");
    const rawTotal = calculateTotal(selectedSeats.size, screeningData ? screeningData.ticket_price : "0");
    totalPriceSpan.textContent = formatMoney(rawTotal);
    ticketLine.textContent = `${selectedSeats.size} × ${formatMoney(screeningData ? screeningData.ticket_price : "0")}`;

    bookButton.disabled = Boolean(screeningData && screeningData.has_started);
  }

  bookButton.addEventListener("click", async () => {
    if (selectedSeats.size === 0) {
      showMessage(messageBox, "error", "Please select at least one seat.");
      return;
    }

    const { user, failed } = await pageUser(getAuth(), messageBox);
    if (failed) return;

    const seatIds = Array.from(selectedSeats);
    const returnDestination = `/seats.html?screening_id=${screeningId}&selected=${formatSelectedSeats(seatIds)}`;

    if (!user) {
      // Provisional seat selection preserved across login
      globalThis.location.assign(loginUrl(returnDestination));
      return;
    }

    if (user.role !== "CUSTOMER") {
      showMessage(messageBox, "error", "Only customer accounts can make bookings.");
      return;
    }

    bookButton.disabled = true;
    clear(messageBox);

    try {
      const response = await getApi().post("/api/bookings", {
        screening_id: Number(screeningId),
        seat_ids: seatIds,
      });
      const booking = response.booking;
      globalThis.location.assign(`/booking.html?id=${booking.booking_id}`);
    } catch (err) {
      bookButton.disabled = false;
      // Refresh the seat map (this also drops seats that were taken from the selection and
      // recalculates the total), THEN explain: loading clears the message box.
      const { ok, removed } = await loadData();
      if (ok) {
        showMessage(messageBox, "error", takenSeatsMessage(removed) || err.message || "Failed to create booking.");
      }
    }
  });

  await loadData();
}

globalThis.addEventListener("DOMContentLoaded", main);
