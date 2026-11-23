// Admin Screening Management (T7, A-02): list, add and edit screenings.
//
// Rules shown here are only explanations; the server and the database decide:
// D2 (a screening with any booking record cannot be changed) answers 409, and an overlap in
// the same room answers 409. The Edit button is disabled for a screening that has bookings.

import { getApi } from "../api.js";
import { badge, dataTable, requireAdmin, screeningEditLock, toInputDateTime } from "../admin.js";
import { formatDateTime, formatMoney } from "../format.js";
import { initNav } from "../nav.js";
import { clear, el, setFieldError, showMessage } from "../ui.js";

const FIELDS = ["movie_id", "room_id", "starts_at", "ends_at", "ticket_price"];

function fill(select, placeholder, items, valueOf, labelOf) {
  clear(select);
  select.append(el("option", { attrs: { value: "" }, text: placeholder }));
  for (const item of items) {
    select.append(el("option", { attrs: { value: String(valueOf(item)) }, text: labelOf(item) }));
  }
}

async function main() {
  await initNav(document.getElementById("site-nav"));

  const messageBox = document.getElementById("message");
  const formSection = document.getElementById("form-section");
  const user = await requireAdmin({
    page: "/admin-screenings.html",
    messageBox,
    hideNode: formSection,
    what: "manage screenings",
  });
  if (!user) return;

  const form = document.getElementById("screening-form");
  const formTitle = document.getElementById("form-title");
  const idInput = document.getElementById("screening-id");
  const movieSelect = document.getElementById("screening-movie");
  const roomSelect = document.getElementById("screening-room");
  const startsInput = document.getElementById("screening-starts-at");
  const endsInput = document.getElementById("screening-ends-at");
  const priceInput = document.getElementById("screening-ticket-price");
  const cancelBtn = document.getElementById("cancel-btn");
  const filterSelect = document.getElementById("filter-movie");
  const container = document.getElementById("screenings-container");

  let movies = [];
  let roomsLoaded = false;

  function clearFormErrors() {
    for (const name of FIELDS) {
      const errorNode = document.getElementById(`error-${name}`);
      const input = form.elements[name];
      if (errorNode && input) setFieldError(input, errorNode, "");
    }
  }

  function resetForm() {
    clearFormErrors();
    form.reset();
    idInput.value = "";
    formTitle.textContent = "Add New Screening";
    cancelBtn.hidden = true;
  }

  function startEdit(screening) {
    clearFormErrors();
    clear(messageBox);
    idInput.value = String(screening.showtime_id);
    movieSelect.value = String(screening.movie_id);
    roomSelect.value = String(screening.room_id);
    startsInput.value = toInputDateTime(screening.starts_at);
    endsInput.value = toInputDateTime(screening.ends_at);
    priceInput.value = screening.ticket_price;
    formTitle.textContent = `Edit Screening #${screening.showtime_id}: ${screening.title}`;
    cancelBtn.hidden = false;
    form.scrollIntoView({ behavior: "smooth" });
  }

  cancelBtn.addEventListener("click", () => {
    resetForm();
    clear(messageBox);
  });

  function statusBadges(screening) {
    const badges = [];
    if (screening.has_bookings) badges.push(badge("wait", "Has bookings (locked)"));
    if (screening.has_started) badges.push(badge("neutral", "Started"));
    if (badges.length === 0) badges.push(badge("ok", "Editable"));
    return el("div", { className: "badges" }, ...badges);
  }

  async function loadMovies() {
    const data = await getApi().get("/api/admin/movies");
    movies = data.movies || [];
    fill(movieSelect, "Select a movie...", movies, (m) => m.movie_id, (m) => m.title);
    fill(filterSelect, "All Movies", movies, (m) => m.movie_id, (m) => m.title);
  }

  async function loadScreenings() {
    clear(container);
    try {
      const movieId = filterSelect.value;
      const query = movieId ? { movie_id: movieId } : undefined;
      const data = await getApi().get("/api/admin/screenings", { query });
      const screenings = data.screenings || [];

      if (!roomsLoaded) {
        fill(roomSelect, "Select a room...", data.rooms || [], (r) => r.room_id, (r) => r.room_name);
        roomsLoaded = true;
      }

      if (screenings.length === 0) {
        container.append(el("p", { className: "muted empty-note" }, "No screenings found."));
        return;
      }

      container.append(
        dataTable(
          [
            { header: "ID", cell: (s) => String(s.showtime_id) },
            { header: "Movie", className: "cell-strong", cell: (s) => s.title },
            { header: "Room", cell: (s) => s.room_name },
            { header: "Start", cell: (s) => formatDateTime(s.starts_at) },
            { header: "End", cell: (s) => formatDateTime(s.ends_at) },
            { header: "Price", cell: (s) => formatMoney(s.ticket_price) },
            { header: "Status", cell: statusBadges },
            {
              header: "Actions",
              className: "cell-actions",
              cell: (s) => {
                const lock = screeningEditLock(s);
                return el("button", {
                  className: "button button-secondary",
                  attrs: { type: "button", disabled: lock.disabled, title: lock.title },
                  text: "Edit",
                  on: { click: () => startEdit(s) },
                });
              },
            },
          ],
          screenings,
        ),
      );
    } catch (err) {
      showMessage(messageBox, "error", err.message || "Failed to load screenings.");
    }
  }

  filterSelect.addEventListener("change", loadScreenings);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFormErrors();
    clear(messageBox);

    const isEdit = Boolean(idInput.value);
    const showtimeId = idInput.value;

    const payload = {
      movie_id: movieSelect.value ? Number.parseInt(movieSelect.value, 10) : null,
      room_id: roomSelect.value ? Number.parseInt(roomSelect.value, 10) : null,
      starts_at: startsInput.value.trim() || null,
      ends_at: endsInput.value.trim() || null,
      ticket_price: priceInput.value.trim() || null,
    };

    try {
      const api = getApi();
      if (isEdit) {
        await api.put(`/api/admin/screenings/${encodeURIComponent(showtimeId)}`, payload);
        showMessage(messageBox, "success", `Screening #${showtimeId} updated successfully.`);
      } else {
        const res = await api.post("/api/admin/screenings", payload);
        showMessage(messageBox, "success", `Screening #${res.screening.showtime_id} created successfully.`);
      }
      resetForm();
      await loadScreenings();
    } catch (err) {
      if (err.fields) {
        for (const [name, message] of Object.entries(err.fields)) {
          const errorNode = document.getElementById(`error-${name}`);
          const input = form.elements[name];
          if (errorNode && input) setFieldError(input, errorNode, message);
        }
      }
      showMessage(messageBox, "error", err.message || "Failed to save screening.");
    }
  });

  try {
    await loadMovies();
  } catch (err) {
    showMessage(messageBox, "error", err.message || "Failed to load movies.");
  }
  await loadScreenings();
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", main);
}
