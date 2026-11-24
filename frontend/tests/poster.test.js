import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { movieCard, movieDetails, movieTile, screeningRow } from "../js/catalog.js";
import { pickFeatured, renderByHall, renderHero } from "../js/home.js";
import { fallbackColour, posterFrame, posterPath } from "../js/poster.js";
import { el } from "../js/ui.js";

class FakeNode {
  constructor(tag) {
    this.tag = tag;
    this.attributes = {};
    this.children = [];
    this.className = "";
    this._text = "";
    this.listeners = {};
    this.hidden = false;
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(""); }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
  addEventListener(name, handler) { this.listeners[name] = handler; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren() { this.children = []; this._text = ""; }
  find(predicate) {
    if (predicate(this)) return this;
    for (const child of this.children) {
      const found = child.find ? child.find(predicate) : null;
      if (found) return found;
    }
    return null;
  }
}
class FakeText {
  constructor(text) { this.text = text; }
  get textContent() { return this.text; }
}

let original;
beforeEach(() => {
  original = globalThis.document;
  globalThis.document = { createElement: (tag) => new FakeNode(tag), createTextNode: (t) => new FakeText(t) };
});
afterEach(() => { globalThis.document = original; });

const MOVIE = { movie_id: 5, title: "Exhuma", genre: "Horror", duration_minutes: 134, rating: "15",
  synopsis: "Shamans move a cursed grave.", release_date: "2024-02-22", poster_url: "/images/posters/exhuma.jpg" };
const img = (node) => node.find((n) => n.tag === "img");

test("only /images/posters/<file>.jpg|png paths are poster paths", () => {
  assert.equal(posterPath("/images/posters/exhuma.jpg"), "/images/posters/exhuma.jpg");
  assert.equal(posterPath("/images/posters/a-b_c.2.png"), "/images/posters/a-b_c.2.png");
  for (const bad of [null, undefined, "", 5, "exhuma.jpg", "/images/exhuma.jpg", "/images/posters/../a.jpg", "/images/posters/x/a.jpg",
    "https://evil.example/images/posters/a.jpg", "//evil.example/a.jpg", "javascript:alert(1)", "/images/posters/a.gif",
    "/images/posters/a.jpg?x=1", `/images/posters/${"a".repeat(260)}.jpg`]) {
    assert.equal(posterPath(bad), null, String(bad));
  }
});

test("a poster is an image with the title as alt text, inside the fixed frame", () => {
  const frame = posterFrame("Exhuma", "/images/posters/exhuma.jpg");
  const image = img(frame);

  assert.match(frame.className, /^poster poster-md poster-c[0-5]$/);
  assert.equal(image.attributes.src, "/images/posters/exhuma.jpg");
  assert.equal(image.attributes.alt, "Exhuma");
  assert.equal(image.attributes.loading, "lazy");
  assert.equal(image.attributes.hidden, undefined);
  const fallback = frame.find((n) => n.className === "poster-fallback");
  assert.equal(fallback.attributes["aria-hidden"], "true", "the title is not read twice while the image shows");
});

test("without a poster path the coloured block with the title is shown, no image at all", () => {
  for (const url of [null, undefined, "", "https://evil.example/a.jpg", "/images/posters/a.gif"]) {
    const frame = posterFrame("Exhuma", url);
    assert.equal(img(frame), null, String(url));
    const fallback = frame.find((n) => n.className === "poster-fallback");
    assert.equal(fallback.textContent, "Exhuma");
    assert.equal(fallback.attributes["aria-hidden"], undefined);
  }
});

test("when the image fails to load, the image is hidden and the title block takes over", () => {
  const frame = posterFrame("Exhuma", "/images/posters/missing.jpg");
  const image = img(frame);
  const fallback = frame.find((n) => n.className === "poster-fallback");

  image.listeners.error();

  assert.equal(image.attributes.hidden, "");
  assert.equal(fallback.attributes["aria-hidden"], undefined);
  assert.equal(fallback.textContent, "Exhuma");
});

test("a title always gets the same fallback colour, in 0..5", () => {
  assert.equal(fallbackColour("Exhuma"), fallbackColour("Exhuma"));
  for (const title of ["", "A", "Exhuma", "20th Century Girl", "한글 제목", null]) {
    const colour = fallbackColour(title);
    assert.ok(Number.isInteger(colour) && colour >= 0 && colour <= 5, String(title));
  }
});

test("el() accepts src and alt only for same-site images", () => {
  const node = el("img", { attrs: { src: "/images/posters/exhuma.jpg", alt: "x", loading: "lazy" } });
  assert.equal(node.attributes.src, "/images/posters/exhuma.jpg");
  for (const bad of ["https://evil.example/a.jpg", "//evil.example/a.jpg", "javascript:alert(1)", "data:image/png;base64,AA", "a.jpg"]) {
    assert.throws(() => el("img", { attrs: { src: bad } }), undefined, bad);
  }
  assert.throws(() => el("img", { attrs: { onerror: "alert(1)" } }));
  assert.throws(() => el("img", { attrs: { srcset: "x" } }));
});

test("posters appear on the movie card, tile, detail and the all-movies schedule row", () => {
  assert.equal(img(movieCard(MOVIE)).attributes.alt, "Exhuma");
  assert.equal(img(movieTile(MOVIE)).attributes.alt, "Exhuma");
  assert.equal(img(movieDetails(MOVIE)[0]).attributes.alt, "Exhuma");
  const screening = { showtime_id: 9, movie_id: 5, title: "Exhuma", poster_url: "/images/posters/exhuma.jpg", room_name: "Hall 2",
    starts_at: "2026-11-25T19:00:00+09:00", ends_at: "2026-11-25T21:14:00+09:00", ticket_price: "12000.00", has_started: false };
  assert.equal(img(screeningRow(screening, { showMovie: true })).attributes.alt, "Exhuma");
  assert.equal(img(screeningRow(screening)), null, "the movie's own schedule does not repeat the poster");
});

test("a movie without a poster still shows its title block everywhere", () => {
  const bare = { ...MOVIE, poster_url: null };
  for (const node of [movieCard(bare), movieTile(bare), movieDetails(bare)[0]]) {
    assert.equal(img(node), null);
    assert.ok(node.find((n) => n.className === "poster-fallback"));
  }
});

// --- home page --------------------------------------------------------------------------

const MOVIES = [MOVIE, { ...MOVIE, movie_id: 6, title: "Godzilla" }];
const S = (id, movie, hour, started) => ({ showtime_id: id, movie_id: movie, title: movie === 5 ? "Exhuma" : "Godzilla",
  room_name: `Hall ${id % 2 + 1}`, starts_at: `2026-11-25T${hour}:00:00+09:00`, has_started: started });

test("the featured movie is the one of the next screening that has not started", () => {
  const screenings = [S(1, 5, "10", true), S(2, 6, "13", false), S(3, 5, "16", false)];
  assert.equal(pickFeatured(MOVIES, screenings).movie_id, 6);
  assert.equal(pickFeatured(MOVIES, [S(1, 5, "10", true)]).movie_id, 5, "nothing left today: the first movie");
  assert.equal(pickFeatured(MOVIES, []).movie_id, 5);
  assert.equal(pickFeatured([], []), null);
});

test("the hero shows poster, facts, rating badge, today's showtimes and a booking link", () => {
  const container = el("section");
  renderHero(container, MOVIE, [S(1, 5, "10", true), S(3, 5, "16", false)]);

  assert.equal(container.hidden, false);
  assert.ok(img(container));
  assert.ok(container.textContent.includes("Horror · 134 min") && container.textContent.includes("Rated 15"));
  const links = [];
  const walk = (n) => { if (n.tag === "a") links.push(n); (n.children ?? []).forEach(walk); };
  walk(container);
  assert.deepEqual(links.map((a) => a.attributes.href), ["/seats.html?screening_id=3", "/movie.html?id=5"]);
  assert.ok(container.textContent.includes("Book tickets"));
  assert.ok(container.find((n) => n.className === "chip chip-closed"), "a started showtime is greyed, not a link");
});

test("today's showtimes are grouped by hall, in hall order", () => {
  const container = el("div");
  renderByHall(container, [S(2, 5, "10", false), S(1, 6, "13", false), S(4, 5, "16", false)]);

  const names = container.children.map((section) => section.children[0].textContent);
  assert.deepEqual(names, ["Hall 1", "Hall 2"]);
});
