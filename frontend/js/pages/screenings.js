// Schedule page: all screenings of one day, every movie (public, no login needed).

import { getApi } from "../api.js";
import { screeningRow } from "../catalog.js";
import { isDateText } from "../format.js";
import { initNav } from "../nav.js";
import { clear, describeError, showMessage } from "../ui.js";

initNav(document.getElementById("site-nav"));

const message = document.getElementById("message");
const schedule = document.getElementById("schedule");
const dateInput = document.getElementById("date");

async function load(day) {
  clear(schedule);
  clear(message);
  try {
    const query = day ? { date: day } : {};
    const body = await getApi().get("/api/screenings", { auth: false, query });
    dateInput.value = body.date;
    if (body.screenings.length === 0) {
      showMessage(message, "info", "There are no screenings on this day.");
      return;
    }
    for (const screening of body.screenings) schedule.append(screeningRow(screening, { showMovie: true }));
  } catch (error) {
    showMessage(message, "error", describeError(error));
  }
}

dateInput.addEventListener("change", () => load(dateInput.value));
const requested = new URLSearchParams(globalThis.location.search).get("date");
load(isDateText(requested) ? requested : "");
