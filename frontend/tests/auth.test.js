// Tests for js/auth.js, js/forms.js and the 401 wiring, with a fake fetch.
// Run: node --test tests/auth.test.js (from frontend/)

import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError, TOKEN_KEY, createApiClient, getApi } from "../js/api.js";
import { ALLOWED_NEXT_PAGES, createAuth, getAuth, loginUrl, safeNext } from "../js/auth.js";
import { clearFormErrors, showFormError } from "../js/forms.js";

const BASE = "http://localhost:5000";

function memoryStorage(initial = {}) {
  const data = new Map(Object.entries(initial));
  return {
    getItem: (key) => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => void data.set(key, String(value)),
    removeItem: (key) => void data.delete(key),
    data,
  };
}

function json(status, body) {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** A client + auth pair with a scripted fetch. `respond(url, init)` returns a Response. */
function setup(respond, { storage = memoryStorage(), here = () => "/", } = {}) {
  const calls = [];
  const navigations = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url: new URL(url).pathname, init });
    return respond(new URL(url).pathname, init);
  };
  let auth;
  const api = createApiClient({ baseUrl: BASE, fetchImpl, storage, onUnauthorized: () => auth.handleUnauthorized() });
  auth = createAuth({ api, navigate: (url) => navigations.push(url), here });
  return { api, auth, calls, navigations, storage };
}

const USER = { user_id: 7, username: "alice", role: "CUSTOMER" };

// --- safeNext: only known pages, never another site --------------------------------------

test("the allow-list contains the known pages and not the login pages", () => {
  assert.ok(ALLOWED_NEXT_PAGES.has("/") && ALLOWED_NEXT_PAGES.has("/index.html"));
  assert.ok(!ALLOWED_NEXT_PAGES.has("/login.html") && !ALLOWED_NEXT_PAGES.has("/register.html"));
});

test("safeNext keeps a known page and a plain query string", () => {
  assert.equal(safeNext("/"), "/");
  assert.equal(safeNext("/index.html"), "/index.html");
  assert.equal(safeNext("/index.html?tab=2&x=a-b_c.d"), "/index.html?tab=2&x=a-b_c.d");
  assert.equal(safeNext("/index.html#section"), "/index.html"); // fragment dropped
});

test("safeNext refuses everything that could leave the site or an unknown page", () => {
  const hostile = [
    "https://evil.example/", "http://evil.example", "//evil.example", "///evil.example", "/\\evil.example",
    "\\\\evil.example", "javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,x", "/login.html",
    "/register.html", "/unknown.html", "/admin/index.html", "/../index.html/../../etc/passwd", "index.html",
    "", " ", null, undefined, 5, {}, ["/index.html"], "/index.html\r\nSet-Cookie: a=b", "/index.html\u0000.js",
    "/" + "a".repeat(300), "/index.html/../../evil", "/%2e%2e/%2e%2e/evil", "/index.html@evil.example",
  ];
  for (const value of hostile) {
    const result = safeNext(value);
    assert.ok(result === "/" || ALLOWED_NEXT_PAGES.has(result.split("?")[0]), `${String(value)} -> ${result}`);
    assert.ok(!result.includes("evil") && !result.includes("javascript"), `${String(value)} -> ${result}`);
  }
  assert.equal(safeNext("/unknown.html"), "/");
  assert.equal(safeNext("/unknown.html", "/index.html"), "/index.html");
});

test("safeNext keeps only a plain or percent-encoded query and drops anything else", () => {
  assert.equal(safeNext("/index.html?a=%3Cb%3E"), "/index.html?a=%3Cb%3E");
  for (const query of ["a=<script>", "a=b c", "a=(x)", "a=b;c", "a=b:c", "a=b,c", "a=*", "a=!", "a=$x",
    "a=@b", "a=~", "a=/b", "a=b?c", "a='x'", 'a="x"']) {
    assert.equal(safeNext(`/index.html?${query}`), "/index.html", query);
  }
  // A backslash anywhere makes the whole value unacceptable (stricter than dropping the query).
  assert.equal(safeNext("/index.html?a=\\x"), "/");
  for (const value of ["/index.html?a=<script>", "/index.html?a=%3Cb%3E", "/index.html?x=1&y=2"]) {
    assert.ok(!/[<>"' ]/.test(safeNext(value)), value);
  }
});

test("loginUrl carries next only when it is a known page other than home", () => {
  assert.equal(loginUrl("/"), "/login.html");
  assert.equal(loginUrl("https://evil.example"), "/login.html");
  assert.equal(loginUrl("/index.html?x=1"), "/login.html?next=%2Findex.html%3Fx%3D1");
});

// --- login / register / logout -----------------------------------------------------------

test("login stores the token for this tab and returns the user; no Authorization is sent", async () => {
  const { auth, calls, storage } = setup((path) =>
    json(200, { token: "tok.en.value", token_type: "Bearer", expires_in: 28800, user: USER }));
  storage.setItem(TOKEN_KEY, "an-old-token");

  const user = await auth.login("alice", "secret");

  assert.deepEqual(user, USER);
  assert.equal(storage.getItem(TOKEN_KEY), "tok.en.value");
  assert.equal(calls[0].url, "/api/auth/login");
  assert.deepEqual(JSON.parse(calls[0].init.body), { username: "alice", password: "secret" });
  assert.equal(calls[0].init.headers.Authorization, undefined);
  assert.equal(calls[0].init.credentials, "omit");
});

test("a failed login stores nothing and does not trigger the 401 redirect", async () => {
  const { auth, navigations, storage } = setup(() =>
    json(401, { error: { code: "invalid_credentials", message: "The account ID or password is incorrect." } }));

  await assert.rejects(auth.login("alice", "wrong"), (error) =>
    error instanceof ApiError && error.code === "invalid_credentials");

  assert.equal(storage.getItem(TOKEN_KEY), null);
  assert.deepEqual(navigations, []);
});

test("register sends only the account ID and password, stores no token and does not log in", async () => {
  const { auth, calls, storage } = setup(() => json(201, { user: USER }));

  const user = await auth.register("alice", "secret");

  assert.deepEqual(user, USER);
  assert.deepEqual(JSON.parse(calls[0].init.body), { username: "alice", password: "secret" });
  assert.deepEqual(Object.keys(JSON.parse(calls[0].init.body)).sort(), ["password", "username"]);
  assert.equal(storage.getItem(TOKEN_KEY), null);
});

test("logout removes the token from sessionStorage immediately and sends no token", async () => {
  const { auth, calls, storage } = setup(() => new Response(null, { status: 204 }));
  storage.setItem(TOKEN_KEY, "tok.en.value");

  const pending = auth.logout();
  assert.equal(storage.getItem(TOKEN_KEY), null, "cleared before the server has answered");
  await pending;

  assert.equal(calls[0].url, "/api/auth/logout");
  assert.equal(calls[0].init.headers.Authorization, undefined);
  assert.equal(await auth.currentUser(), null);
});

test("logout still logs out locally when the server cannot be reached", async () => {
  const { auth, storage } = setup(() => { throw new TypeError("Failed to fetch"); });
  storage.setItem(TOKEN_KEY, "tok.en.value");

  await auth.logout(); // must not throw

  assert.equal(storage.getItem(TOKEN_KEY), null);
});

// --- who am I ------------------------------------------------------------------------------

test("currentUser without a token is null and asks nobody", async () => {
  const { auth, calls } = setup(() => json(200, { user: USER }));

  assert.equal(await auth.currentUser(), null);
  assert.equal(calls.length, 0);
});

test("currentUser asks the server with the token and caches the answer", async () => {
  const { auth, calls, storage } = setup(() => json(200, { user: USER }));
  storage.setItem(TOKEN_KEY, "tok.en.value");

  assert.deepEqual(await auth.currentUser(), USER);
  assert.deepEqual(await auth.currentUser(), USER);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].init.headers.Authorization, "Bearer tok.en.value");
  await auth.currentUser({ refresh: true });
  assert.equal(calls.length, 2);
});

test("a 401 for the token clears it, returns null and redirects to the login page", async () => {
  const { auth, navigations, storage } = setup(
    () => json(401, { error: { code: "unauthorized", message: "Authentication is required." } }),
    { here: () => "/index.html?tab=2" },
  );
  storage.setItem(TOKEN_KEY, "expired.token");

  assert.equal(await auth.currentUser(), null);

  assert.equal(storage.getItem(TOKEN_KEY), null);
  assert.deepEqual(navigations, ["/login.html?next=%2Findex.html%3Ftab%3D2"]);
});

test("currentUser rethrows server and network errors instead of pretending to be logged out", async () => {
  const { auth, storage, navigations } = setup(() => json(503, { error: { code: "database_unavailable", message: "x" } }));
  storage.setItem(TOKEN_KEY, "tok.en.value");

  await assert.rejects(auth.currentUser(), (error) => error.status === 503);

  assert.equal(storage.getItem(TOKEN_KEY), "tok.en.value", "a server error is not a logout");
  assert.deepEqual(navigations, []);
});

// --- the redirect after a 401 --------------------------------------------------------------

test("the redirect keeps only a safe destination and never loops on the login pages", () => {
  const cases = [
    ["/index.html", "/login.html?next=%2Findex.html"],
    ["/", "/login.html"],
    ["/unknown/page.html?a=1", "/login.html"],
    ["/index.html?a=<script>", "/login.html?next=%2Findex.html"],
    ["/index.html?a=(x)", "/login.html?next=%2Findex.html"],
  ];
  for (const [here, expected] of cases) {
    const navigations = [];
    const auth = createAuth({ api: {}, navigate: (url) => navigations.push(url), here: () => here });
    auth.handleUnauthorized();
    assert.deepEqual(navigations, [expected], here);
  }
  for (const here of ["/login.html", "/login.html?next=%2F", "/register.html", "/register.html?x=1"]) {
    const navigations = [];
    createAuth({ api: {}, navigate: (url) => navigations.push(url), here: () => here }).handleUnauthorized();
    assert.deepEqual(navigations, [], `${here} must not redirect to itself`);
  }
});

test("a token sent to the API that answers 401 on any protected call leads to the login page", async () => {
  const { api, navigations, storage } = setup(
    () => json(401, { error: { code: "unauthorized", message: "Authentication is required." } }),
    { here: () => "/index.html" },
  );
  storage.setItem(TOKEN_KEY, "expired.token");

  await assert.rejects(api.get("/api/bookings"), (error) => error.status === 401);

  assert.equal(storage.getItem(TOKEN_KEY), null);
  assert.deepEqual(navigations, ["/login.html?next=%2Findex.html"]);
});

test("the shared client is wired to the same redirect through getAuth()", async () => {
  globalThis.APP_CONFIG = { apiBaseUrl: BASE };
  const storage = memoryStorage({ [TOKEN_KEY]: "expired.token" });
  getApi({
    fetchImpl: async () => json(401, { error: { code: "unauthorized", message: "Authentication is required." } }),
    storage,
  });
  const auth = getAuth();
  assert.equal(getAuth(), auth, "one shared instance");

  // getAuth's own navigate/here use `location`, which Node does not have: provide a fake
  const seen = [];
  globalThis.location = { pathname: "/index.html", search: "", assign: (url) => seen.push(url) };
  await assert.rejects(getApi().get("/api/bookings"), (error) => error.status === 401);

  assert.deepEqual(seen, ["/login.html?next=%2Findex.html"]);
  assert.equal(storage.getItem(TOKEN_KEY), null);
  delete globalThis.location;
});

// --- form error display --------------------------------------------------------------------

function fakeField() {
  const attributes = {};
  return {
    input: { setAttribute: (n, v) => { attributes[n] = v; }, removeAttribute: (n) => { delete attributes[n]; }, attributes },
    error: { textContent: "", hidden: true },
  };
}

function fakeMessageBox() {
  return {
    children: [],
    replaceChildren() { this.children = []; },
    append(node) { this.children.push(node); },
  };
}

test("field messages from the server go next to their inputs, as text", () => {
  globalThis.document = { createElement: () => ({ setAttribute() {}, append() {}, addEventListener() {}, set textContent(v) { this._t = v; }, get textContent() { return this._t; } }), createTextNode: (t) => t };
  const fields = { username: fakeField(), password: fakeField() };
  const box = fakeMessageBox();
  const error = new ApiError({ status: 400, code: "validation_error", message: "Fix.",
    fields: { username: "<b>Account ID is required.</b>", unknown_field: "ignored", __proto__x: "x" } });

  const shown = showFormError(error, fields, box);

  assert.equal(shown, true);
  assert.equal(fields.username.error.textContent, "<b>Account ID is required.</b>");
  assert.equal(fields.username.error.hidden, false);
  assert.equal(fields.username.input.attributes["aria-invalid"], "true");
  assert.equal(fields.password.error.hidden, true);
  assert.equal(box.children.length, 0);

  clearFormErrors(fields, box);
  assert.equal(fields.username.error.textContent, "");
  assert.equal(fields.username.error.hidden, true);
  assert.equal(fields.username.input.attributes["aria-invalid"], undefined);
  delete globalThis.document;
});

test("other errors become one message in the message box", () => {
  const created = [];
  globalThis.document = {
    createElement: (tag) => { const node = { tag, attributes: {}, setAttribute(n, v) { this.attributes[n] = v; }, append() {}, addEventListener() {}, className: "" };
      Object.defineProperty(node, "textContent", { set(v) { node._t = v; }, get() { return node._t; } }); created.push(node); return node; },
    createTextNode: (t) => t,
  };
  const fields = { username: fakeField(), password: fakeField() };
  const box = fakeMessageBox();

  const shown = showFormError(new ApiError({ status: 401, code: "invalid_credentials", message: "The account ID or password is incorrect." }), fields, box);

  assert.equal(shown, false);
  assert.equal(box.children.length, 1);
  assert.equal(box.children[0].textContent, "The account ID or password is incorrect.");
  assert.equal(box.children[0].attributes.role, "alert");
  delete globalThis.document;
});
