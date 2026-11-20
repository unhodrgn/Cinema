// Movie list page: every registered movie (public, no login needed).

import { getApi } from "../api.js";
import { movieCard } from "../catalog.js";
import { initNav } from "../nav.js";
import { clear, describeError, showMessage } from "../ui.js";

initNav(document.getElementById("site-nav"));

const message = document.getElementById("message");
const list = document.getElementById("movies");

async function main() {
  try {
    const { movies } = await getApi().get("/api/movies", { auth: false });
    clear(list);
    if (movies.length === 0) {
      showMessage(message, "info", "No movies are registered yet.");
      return;
    }
    clear(message);
    for (const movie of movies) list.append(movieCard(movie));
  } catch (error) {
    showMessage(message, "error", describeError(error));
  }
}

main();
