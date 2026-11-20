// Admin booking list (T8, A-03): every booking of every customer, view only.
// Filters: status, screening ID, user ID. The server expires overdue bookings before answering.

import { getApi } from "../api.js";
import { dataTable, requireAdmin } from "../admin.js";
import { bookingColumns, readFilters } from "../admin_bookings.js";
import { initNav } from "../nav.js";
import { clear, el, showMessage } from "../ui.js";

async function main() {
  await initNav(document.getElementById("site-nav"));

  const messageBox = document.getElementById("message");
  const filterSection = document.getElementById("filter-section");
  const user = await requireAdmin({
    page: "/admin-bookings.html",
    messageBox,
    hideNode: filterSection,
    what: "view all bookings",
  });
  if (!user) return;

  const form = document.getElementById("filter-form");
  const statusSelect = document.getElementById("filter-status");
  const screeningInput = document.getElementById("filter-screening");
  const userInput = document.getElementById("filter-user");
  const clearBtn = document.getElementById("clear-btn");
  const filterError = document.getElementById("error-filters");
  const summary = document.getElementById("summary");
  const container = document.getElementById("bookings-container");

  function showFilterProblems(problems) {
    const labels = { status: "Status", screening_id: "Screening ID", user_id: "User ID" };
    const text = Object.entries(problems)
      .map(([name, message]) => `${labels[name] ?? name}: ${message}`)
      .join(" ");
    filterError.textContent = text;
    filterError.hidden = text === "";
  }

  async function loadBookings() {
    clear(messageBox);
    clear(container);
    summary.textContent = "";

    const { query, problems } = readFilters({
      status: statusSelect.value,
      screeningId: screeningInput.value,
      userId: userInput.value,
    });
    showFilterProblems(problems);
    if (Object.keys(problems).length > 0) return;

    try {
      const data = await getApi().get("/api/admin/bookings", { query });
      const bookings = data.bookings || [];
      summary.textContent = `${bookings.length} booking${bookings.length === 1 ? "" : "s"}`;

      if (bookings.length === 0) {
        container.append(el("p", { className: "muted empty-note" }, "No bookings match these filters."));
        return;
      }
      container.append(dataTable(bookingColumns(), bookings));
    } catch (err) {
      if (err.fields) showFilterProblems(err.fields);
      showMessage(messageBox, "error", err.message || "Failed to load bookings.");
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    loadBookings();
  });
  clearBtn.addEventListener("click", () => {
    form.reset();
    loadBookings();
  });

  await loadBookings();
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", main);
}
