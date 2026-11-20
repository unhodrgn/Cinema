// Tests for js/catalog.js with a minimal fake DOM. Run: node --test tests/catalog.test.js

import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { movieCard, movieDetails, movieFacts, movieHref, screeningRow } from "../js/catalog.js";

class FakeNode {
  constructor(tag) {
    this.tag = tag;
    this.attributes = {};
    this.children = [];
    this.className = "";
    this._text = "";
  }
  set innerHTML(value) { throw new Error("innerHTML must not be used"); }
  set outerHTML(value) { throw new Error("outerHTML must not be used"); }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(""); }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener() {}
  append(...nodes) { this.children.push(...nodes); }
  find(predicate) {
    if (predicate(this)) return this;
    for (const child of this.children) {
      const found = child.find ? child.find(predicate) : (predicate(child) ? child : null);
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

const MOVIE = { movie_id: 3, title: "Phim 3", genre: "Comedy", duration_minutes: 140, rating: "15",
  synopsis: "Demo movie 3", release_date: "2026-10-01" };
const HOSTILE = '<img src=x onerror=alert(1)><script>alert(2)</script>';

test("movie links are built only from usable ids", () => {
  assert.equal(movieHref(3), "/movie.html?id=3");
  assert.equal(movieHref("42"), "/movie.html?id=42");
  for (const bad of ["0", -1, "1;alert(1)", "../x", "javascript:alert(1)", null, undefined, "1 2", 1.5]) {
    assert.equal(movieHref(bad), null, String(bad));
  }
});

test("movie facts skip what is missing", () => {
  assert.equal(movieFacts(MOVIE), "Comedy · Rated 15 · 140 min");
  assert.equal(movieFacts({ ...MOVIE, genre: null, rating: null }), "140 min");
  assert.equal(movieFacts({ ...MOVIE, genre: "", rating: "", duration_minutes: 90 }), "90 min");
});

test("a movie card links to its page and shows the synopsis as text", () => {
  const card = movieCard(MOVIE);

  const link = card.find((n) => n.tag === "a");
  assert.equal(link.attributes.href, "/movie.html?id=3");
  assert.equal(link.textContent, "Phim 3");
  assert.ok(card.textContent.includes("Demo movie 3"));
  assert.ok(card.textContent.includes("Comedy · Rated 15 · 140 min"));
});

test("hostile movie text is only ever text, never markup", () => {
  const card = movieCard({ ...MOVIE, title: HOSTILE, genre: HOSTILE, synopsis: HOSTILE });
  const details = movieDetails({ ...MOVIE, title: HOSTILE, genre: HOSTILE, rating: HOSTILE, synopsis: HOSTILE });

  assert.ok(card.textContent.includes(HOSTILE));
  const texts = [];
  const walk = (node) => { if (node instanceof FakeText) texts.push(node.text); (node.children ?? []).forEach(walk); };
  walk(card); details.forEach(walk);
  assert.ok(texts.length === 0 || texts.every((t) => typeof t === "string"));
  // nothing created a script/img element from the text: only the known tags exist
  const tags = new Set();
  const collect = (node) => { if (node.tag) tags.add(node.tag); (node.children ?? []).forEach(collect); };
  collect(card); details.forEach(collect);
  assert.ok(!tags.has("script") && !tags.has("img"), [...tags].join());
});

test("a movie with a bad id is shown without a link instead of a dangerous one", () => {
  const card = movieCard({ ...MOVIE, movie_id: "1;alert(1)" });

  assert.equal(card.find((n) => n.tag === "a"), null);
  assert.ok(card.textContent.includes("Phim 3"));
});

test("movie details show the six attributes and 'Not given' for empty ones", () => {
  const nodes = movieDetails({ ...MOVIE, genre: null, rating: null, synopsis: null, release_date: null });
  const text = nodes.map((n) => n.textContent).join("|");

  assert.ok(text.includes("Phim 3") && text.includes("140 min"));
  assert.equal((text.match(/Not given/g) ?? []).length, 4); // genre, rating, release date, synopsis
});

const SCREENING = { showtime_id: 9, movie_id: 3, title: "Phim 3", room_id: 2, room_name: "Phòng 2",
  starts_at: "2026-11-25T19:00:00+09:00", ends_at: "2026-11-25T21:20:00+09:00", ticket_price: "12000.00",
  has_started: false };

test("a screening row shows the time range, room and price per seat", () => {
  const row = screeningRow(SCREENING);

  assert.ok(row.textContent.includes("19:00 - 21:20"));
  assert.ok(row.textContent.includes("Phòng 2"));
  assert.ok(row.textContent.includes("Price per seat: 12,000"));
  assert.ok(!row.textContent.includes("Phim 3"), "the movie is named only in the all-movies view");
  assert.ok(!row.textContent.includes("Already started"));
});

test("the all-movies view names the movie as a link", () => {
  const row = screeningRow(SCREENING, { showMovie: true });

  const link = row.find((n) => n.tag === "a");
  assert.equal(link.attributes.href, "/movie.html?id=3");
  assert.equal(link.textContent, "Phim 3");
});

test("a started screening is marked, from the server's flag only", () => {
  const started = screeningRow({ ...SCREENING, has_started: true });
  const notStarted = screeningRow({ ...SCREENING, has_started: false });

  assert.ok(started.textContent.includes("Already started"));
  assert.ok(!notStarted.textContent.includes("Already started"));
});

test("screening text from the API is only text", () => {
  const row = screeningRow({ ...SCREENING, room_name: HOSTILE, title: HOSTILE }, { showMovie: true });

  assert.ok(row.textContent.includes(HOSTILE));
  assert.equal(row.find((n) => n.tag === "script" || n.tag === "img"), null);
});
