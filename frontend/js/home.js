// Home page pieces built from API data: the featured movie, the "Now Showing" grid and
// today's showtimes by hall. Everything is placed as text through ui.js (no HTML parsing).

import { movieHref, movieTile } from "./catalog.js";
import { formatDuration, formatTime } from "./format.js";
import { posterFrame } from "./poster.js";
import { clear, el } from "./ui.js";

/** The movie of the next screening that has not started today; else the first movie; else null. */
export function pickFeatured(movies, screenings) {
  const next = screenings.find((screening) => !screening.has_started);
  const byNext = next && movies.find((movie) => movie.movie_id === next.movie_id);
  return byNext ?? movies[0] ?? null;
}

/** One showtime button: a link to the seat map, or a greyed time when it has started. */
function showtimeChip(screening, { withTitle = false } = {}) {
  const label = [el("span", { className: "chip-time", text: formatTime(screening.starts_at) })];
  if (withTitle) label.push(el("span", { className: "chip-title", text: screening.title }));
  if (screening.has_started || !screening.showtime_id) {
    return el("li", {}, el("span", { className: "chip chip-closed" }, ...label));
  }
  return el("li", {}, el("a", {
    className: "chip",
    attrs: { href: `/seats.html?screening_id=${screening.showtime_id}` },
  }, ...label));
}

/** Fill the featured-movie section. `todays` are today's screenings of that movie. */
export function renderHero(container, movie, todays) {
  clear(container);
  const href = movieHref(movie.movie_id);
  const facts = [movie.genre, formatDuration(movie.duration_minutes)].filter(Boolean).join(" · ");
  const meta = el("p", { className: "hero-facts" }, facts);
  if (movie.rating) meta.append(el("span", { className: "badge badge-rating", text: `Rated ${movie.rating}` }));

  const times = todays.length === 0
    ? el("p", { className: "muted", text: "No screenings today." })
    : el("ul", { className: "chip-list", attrs: { "aria-label": "Today's showtimes" } }, ...todays.map((s) => showtimeChip(s)));

  container.append(
    posterFrame(movie.title, movie.poster_url, { size: "lg" }),
    el("div", { className: "hero-body" },
      el("p", { className: "eyebrow", text: "Featured" }),
      el("h2", { className: "hero-title", text: movie.title }),
      meta,
      movie.synopsis ? el("p", { className: "synopsis", text: movie.synopsis }) : null,
      el("h3", { className: "hero-subtitle", text: "Today's showtimes" }),
      times,
      href ? el("a", { className: "button", attrs: { href }, text: "Book tickets" }) : null),
  );
  container.hidden = false;
}

/** Fill the "Now Showing" poster grid. */
export function renderNowShowing(container, movies) {
  clear(container);
  for (const movie of movies) container.append(movieTile(movie));
}

/** Today's showtimes grouped by hall (room names sort as text: "Hall 1" .. "Hall 5"). */
export function renderByHall(container, screenings) {
  clear(container);
  const halls = new Map();
  for (const screening of screenings) {
    if (!halls.has(screening.room_name)) halls.set(screening.room_name, []);
    halls.get(screening.room_name).push(screening);
  }
  for (const name of [...halls.keys()].sort()) {
    container.append(el("section", { className: "hall card" },
      el("h3", { text: name }),
      el("ul", { className: "chip-list chip-list-stacked" },
        ...halls.get(name).map((s) => showtimeChip(s, { withTitle: true })))));
  }
}
