// Builds the catalog's page elements from API data. Every value is placed as text through
// ui.js (no HTML parsing), and links are built only from validated integer ids.

import { formatDuration, formatMoney, formatTimeRange, isIdText } from "./format.js";
import { el } from "./ui.js";

/** `/movie.html?id=3` for a usable id, else null (the title is then shown without a link). */
export function movieHref(movieId) {
  const text = String(movieId);
  return isIdText(text) ? `/movie.html?id=${text}` : null;
}

/** The small grey line under a title: genre, rating, running time (missing parts are left out). */
export function movieFacts(movie) {
  return [
    movie.genre,
    movie.rating ? `Rated ${movie.rating}` : null,
    formatDuration(movie.duration_minutes),
  ].filter(Boolean).join(" · ");
}

/** A card for the movie list. */
export function movieCard(movie) {
  const href = movieHref(movie.movie_id);
  const title = href
    ? el("a", { attrs: { href }, text: movie.title })
    : el("span", { text: movie.title });
  const children = [el("h2", { className: "movie-title" }, title)];
  const facts = movieFacts(movie);
  if (facts) children.push(el("p", { className: "muted", text: facts }));
  if (movie.synopsis) children.push(el("p", { className: "synopsis", text: movie.synopsis }));
  return el("article", { className: "card movie-card" }, ...children);
}

/** The detail block of one movie: the six approved attributes, "not given" when empty. */
export function movieDetails(movie) {
  const rows = [
    ["Genre", movie.genre],
    ["Running time", formatDuration(movie.duration_minutes)],
    ["Rating", movie.rating],
    ["Release date", movie.release_date],
  ];
  const list = el("dl", { className: "facts" });
  for (const [label, value] of rows) {
    list.append(el("dt", { text: label }), el("dd", { text: value || "Not given" }));
  }
  return [
    el("h1", { text: movie.title }),
    list,
    el("h2", { text: "Synopsis" }),
    el("p", { className: "synopsis", text: movie.synopsis || "Not given" }),
  ];
}

/**
 * One line of a schedule. `showMovie` adds the movie title as a link (the all-movies view).
 * A screening that has already started is shown as closed: that is only the database's
 * `has_started` flag being displayed, the booking rule itself is enforced by the server.
 */
export function screeningRow(screening, { showMovie = false } = {}) {
  const parts = [el("strong", { className: "time", text: formatTimeRange(screening.starts_at, screening.ends_at) })];
  if (showMovie) {
    const href = movieHref(screening.movie_id);
    parts.push(href ? el("a", { attrs: { href }, text: screening.title }) : el("span", { text: screening.title }));
  }
  parts.push(
    el("span", { text: screening.room_name }),
    el("span", { className: "muted", text: `Price per seat: ${formatMoney(screening.ticket_price)}` }),
  );
  if (screening.has_started) {
    parts.push(el("span", { className: "badge badge-neutral", text: "Already started" }));
  } else if (screening.showtime_id) {
    parts.push(el("a", { attrs: { href: `/seats.html?screening_id=${screening.showtime_id}` }, text: "Select Seats" }));
  }
  return el("li", { className: "screening" }, ...parts);
}
