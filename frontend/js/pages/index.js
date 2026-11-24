// Home page: the featured movie, the "Now Showing" grid and today's showtimes by hall (public).
// If the API cannot be reached, say so.

import { getApi } from "../api.js";
import { pickFeatured, renderByHall, renderHero, renderNowShowing } from "../home.js";
import { initNav } from "../nav.js";
import { describeError, showMessage } from "../ui.js";

async function main() {
  initNav(document.getElementById("site-nav"));
  const message = document.getElementById("status-message");
  try {
    const api = getApi();
    const [{ movies }, today] = await Promise.all([
      api.get("/api/movies", { auth: false }),
      api.get("/api/screenings", { auth: false }),
    ]);
    if (movies.length === 0) {
      showMessage(message, "info", "No movies are registered yet.");
      return;
    }
    const featured = pickFeatured(movies, today.screenings);
    renderHero(document.getElementById("hero"), featured, today.screenings.filter((s) => s.movie_id === featured.movie_id));
    renderNowShowing(document.getElementById("now-showing"), movies);
    renderByHall(document.getElementById("today-by-hall"), today.screenings);
    document.getElementById("home-sections").hidden = false;
    document.getElementById("today-date").textContent = today.date;
  } catch (error) {
    showMessage(message, "error", describeError(error));
  }
}

main();
