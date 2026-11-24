// Movie posters: a fixed 2:3 frame (CSS) holding the poster image, with a coloured block that
// shows the title when there is no poster or the file cannot be loaded.
// Poster paths come from the API, so only /images/posters/<file>.jpg|png is ever used as `src`.

import { el } from "./ui.js";

const POSTER_PATH = /^\/images\/posters\/[A-Za-z0-9][A-Za-z0-9._-]*\.(jpg|png)$/;
const FALLBACK_COLOURS = 6; // poster-c0 .. poster-c5 in style.css

/** The path if it is a usable poster path, else null. */
export function posterPath(value) {
  return typeof value === "string" && value.length <= 255 && POSTER_PATH.test(value) ? value : null;
}

/** 0..5, the same for the same title (so a movie keeps its colour on every page). */
export function fallbackColour(title) {
  let sum = 0;
  for (const character of String(title ?? "")) sum += character.codePointAt(0);
  return sum % FALLBACK_COLOURS;
}

/**
 * The poster of a movie. `size`: "sm" | "md" | "lg" (only changes the title's font size).
 * The title is always in the DOM: as the image's alt text, or as the fallback block's text.
 */
export function posterFrame(title, posterUrl, { size = "md" } = {}) {
  const src = posterPath(posterUrl);
  const fallback = el("span", {
    className: "poster-fallback",
    text: title ?? "",
    attrs: src ? { "aria-hidden": "true" } : {},
  });
  const frame = el("div", { className: `poster poster-${size} poster-c${fallbackColour(title)}` }, fallback);
  if (src) {
    const image = el("img", {
      className: "poster-img",
      attrs: { src, alt: title ?? "", loading: "lazy", decoding: "async" },
      on: {
        error: () => { // missing or broken file: show the coloured block instead
          image.setAttribute("hidden", "");
          fallback.removeAttribute("aria-hidden");
        },
      },
    });
    frame.append(image);
  }
  return frame;
}
