// Tests for js/nav.js: the three navigation states. Run: node --test tests/nav.test.js (from frontend/)

import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { ApiError, TOKEN_KEY, createApiClient } from "../js/api.js";
import { createAuth } from "../js/auth.js";
import { initNav } from "../js/nav.js";

class FakeNode {
  constructor(tag) {
    this.tag = tag;
    this.attributes = {};
    this.children = [];
    this.className = "";
    this._text = "";
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(""); }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener() {}
  replaceChildren() { this.children = []; this._text = ""; }
  append(...nodes) { this.children.push(...nodes); }
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

const labels = (container) => container.children.map((child) => child.textContent);

const NETWORK_ERROR = new ApiError({ code: "network_error", message: "The server cannot be reached. Please check that it is running." });
const fakeAuth = (result) => ({
  currentUser: async () => { if (result instanceof Error) throw result; return result; },
  logout: async () => {},
});

test("logged out (no user): public links plus Log in and Register", async () => {
  const nav = new FakeNode("nav");
  await initNav(nav, { auth: fakeAuth(null) });
  assert.deepEqual(labels(nav), ["Home", "Movies", "Schedule", "Log in", "Register"]);
});

test("logged in as a customer or an administrator: role links, the account and Log out", async () => {
  const customer = new FakeNode("nav");
  await initNav(customer, { auth: fakeAuth({ user_id: 2, username: "alice", role: "CUSTOMER" }) });
  assert.deepEqual(labels(customer), ["Home", "Movies", "Schedule", "My Bookings", "alice (CUSTOMER)", "Log out"]);

  const admin = new FakeNode("nav");
  await initNav(admin, { auth: fakeAuth({ user_id: 1, username: "root", role: "ADMIN" }) });
  assert.deepEqual(labels(admin), ["Home", "Movies", "Schedule", "Movies (Admin)", "Screenings (Admin)",
    "All Bookings", "root (ADMIN)", "Log out"]);
});

test("API unreachable: no Log in / Register, a neutral state instead", async () => {
  const nav = new FakeNode("nav");
  await initNav(nav, { auth: fakeAuth(NETWORK_ERROR) });
  assert.deepEqual(labels(nav), ["Home", "Movies", "Schedule", "Account unavailable"]);
  assert.ok(!labels(nav).some((label) => /Log in|Register/.test(label)));
});

test("a server error (5xx) is the same neutral state", async () => {
  const nav = new FakeNode("nav");
  const error = Object.assign(new Error("Something went wrong on the server."), { status: 503 });
  await initNav(nav, { auth: fakeAuth(error) });
  assert.deepEqual(labels(nav), ["Home", "Movies", "Schedule", "Account unavailable"]);
});

function realAuth(respond, storage) {
  const api = createApiClient({ baseUrl: "http://localhost:5000", fetchImpl: async (url) => respond(new URL(url).pathname), storage });
  return createAuth({ api, navigate: () => {}, here: () => "/" });
}
const memory = (initial = {}) => {
  const data = new Map(Object.entries(initial));
  return { getItem: (k) => (data.has(k) ? data.get(k) : null), setItem: (k, v) => void data.set(k, String(v)), removeItem: (k) => void data.delete(k) };
};

test("end to end with the real auth: a token and a dead API never shows Log in / Register", async () => {
  const nav = new FakeNode("nav");
  const auth = realAuth(() => { throw new TypeError("fetch failed"); }, memory({ [TOKEN_KEY]: "a-token" }));
  await initNav(nav, { auth });
  assert.deepEqual(labels(nav), ["Home", "Movies", "Schedule", "Account unavailable"]);
});

test("end to end with the real auth: a 401 for the token is logged out, and no token never asks the API", async () => {
  const unauthorized = new Response(JSON.stringify({ error: { code: "invalid_token", message: "Your session is not valid." } }),
    { status: 401, headers: { "Content-Type": "application/json" } });
  const withToken = new FakeNode("nav");
  await initNav(withToken, { auth: realAuth(() => unauthorized, memory({ [TOKEN_KEY]: "stale" })) });
  assert.deepEqual(labels(withToken), ["Home", "Movies", "Schedule", "Log in", "Register"]);

  let asked = 0;
  const noToken = new FakeNode("nav");
  await initNav(noToken, { auth: realAuth(() => { asked += 1; throw new TypeError("never"); }, memory()) });
  assert.deepEqual(labels(noToken), ["Home", "Movies", "Schedule", "Log in", "Register"]);
  assert.equal(asked, 0);
});
