// Movie detail page: the movie, and its screenings for one day (public, no login needed).

import { getApi } from "../api.js";
import { movieDetails, screeningRow } from "../catalog.js";
import { isDateText, isIdText } from "../format.js";
import { initNav } from "../nav.js";
import { clear, describeError, showMessage } from "../ui.js";

initNav(document.getElementById("site-nav"));

const message = document.getElementById("message");
const details = document.getElementById("details");
const schedule = document.getElementById("schedule");
const dateInput = document.getElementById("date");
const scheduleMessage = document.getElementById("schedule-message");
const scheduleSection = document.getElementById("schedule-section");

const params = new URLSearchParams(globalThis.location.search);
const movieId = params.get("id");

async function loadSchedule(day) {
  clear(schedule);
  clear(scheduleMessage);
  try {
    const query = { movie_id: movieId };
    if (day) query.date = day;
    const body = await getApi().get("/api/screenings", { auth: false, query });
    dateInput.value = body.date; // the server's date (today in the cinema's time zone by default)
    if (body.screenings.length === 0) {
      showMessage(scheduleMessage, "info", "There are no screenings on this day.");
      return;
    }
    for (const screening of body.screenings) schedule.append(screeningRow(screening));
  } catch (error) {
    showMessage(scheduleMessage, "error", describeError(error));
  }
}

async function main() {
  if (!isIdText(movieId)) {
    showMessage(message, "error", "This movie could not be found.");
    return;
  }
  try {
    const { movie } = await getApi().get(`/api/movies/${movieId}`, { auth: false });
    clear(details);
    for (const node of movieDetails(movie)) details.append(node);
    document.title = `${movie.title} - Cinema Reservation`;
  } catch (error) {
    showMessage(message, "error", error.status === 404 ? "This movie could not be found." : describeError(error));
    return;
  }
  scheduleSection.hidden = false;
  dateInput.addEventListener("change", () => loadSchedule(dateInput.value));
  const requested = params.get("date");
  await loadSchedule(isDateText(requested) ? requested : "");
}

main();
