// Seat picker page: loads screening and seat availability, enables provisional seat selection,
// preserves selection on login redirect, and proceeds to booking creation when authenticated.

import { getApi } from "../api.js";
import { getAuth, loginUrl } from "../auth.js";
import { formatMoney, formatTimeRange } from "../format.js";
import { initNav } from "../nav.js";
import {
  calculateTotal,
  formatSelectedSeats,
  groupSeatsByRow,
  parseSelectedSeats,
  seatLabel,
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
      renderScreeningInfo();
      renderSeatGrid();
      updateSummary();
      pickerCard.hidden = false;
    } catch (err) {
      pickerCard.hidden = true;
      showMessage(messageBox, "error", err.message || "Failed to load seats.");
    }
  }

  function renderScreeningInfo() {
    clear(infoContainer);
    if (!screeningData) return;

    const titleEl = el("h2", { text: screeningData.title });
    const timeEl = el("p", {
      text: `${formatTimeRange(screeningData.starts_at, screeningData.ends_at)} · ${screeningData.room_name}`,
    });
    const priceEl = el("p", {
      className: "muted",
      text: `Price per seat: ${formatMoney(screeningData.ticket_price)}`,
    });
    infoContainer.append(titleEl, timeEl, priceEl);

    if (screeningData.has_started) {
      infoContainer.append(
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
      rowEl.append(el("span", { className: "seat-row-label", text: rowLetter }));

      for (const seat of seatsInRow) {
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
      gridContainer.append(rowEl);
    }
  }

  function updateSummary() {
    if (selectedSeats.size === 0) {
      selectedListSpan.textContent = "None";
      totalPriceSpan.textContent = "0";
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

    bookButton.disabled = Boolean(screeningData && screeningData.has_started);
  }

  bookButton.addEventListener("click", async () => {
    if (selectedSeats.size === 0) {
      showMessage(messageBox, "error", "Please select at least one seat.");
      return;
    }

    const auth = getAuth();
    let user = null;
    try {
      user = await auth.currentUser();
    } catch {
      user = null;
    }

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
      showMessage(messageBox, "error", err.message || "Failed to create booking.");
      // If seats became unavailable, reload seat data to show updated state
      await loadData();
    }
  });

  await loadData();
}

globalThis.addEventListener("DOMContentLoaded", main);
