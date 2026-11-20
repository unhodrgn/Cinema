// Tests for js/api.js with a fake fetch. Run: node --test tests/api.test.js (from frontend/)

import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError, TOKEN_KEY, assertApiPath, createApiClient, normalizeBaseUrl } from "../js/api.js";

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

/** A fake fetch that records calls and answers with `respond(url, init)`. */
function fakeFetch(respond) {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, init });
    return respond(url, init);
  };
  fetchImpl.calls = calls;
  return fetchImpl;
}

function jsonResponse(status, body) {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function client(respond, options = {}) {
  const fetchImpl = fakeFetch(respond);
  const storage = options.storage ?? memoryStorage();
  const api = createApiClient({ baseUrl: BASE, fetchImpl, storage, ...options });
  return { api, fetchImpl, storage };
}

async function rejection(promise) {
  try {
    await promise;
  } catch (error) {
    return error;
  }
  assert.fail("expected the promise to reject");
}

// --- configuration ------------------------------------------------------------------

test("normalizeBaseUrl accepts only a plain http(s) origin", () => {
  assert.equal(normalizeBaseUrl("http://localhost:5000"), "http://localhost:5000");
  assert.equal(normalizeBaseUrl("http://localhost:5000/"), "http://localhost:5000");
  assert.equal(normalizeBaseUrl("https://api.example.org:443"), "https://api.example.org");
  for (const bad of [undefined, null, "", "  ", "*", "localhost:5000", "ftp://x", "http://x/api",
    "http://x?y=1", "http://x#z", "http://u:p@x", "javascript:alert(1)", "http://*.x.org"]) {
    assert.throws(() => normalizeBaseUrl(bad), undefined, String(bad));
  }
});

test("a client cannot be created without a valid base URL", () => {
  assert.throws(() => createApiClient({ baseUrl: undefined, fetchImpl: async () => {} }));
  assert.throws(() => createApiClient({ baseUrl: "http://x/path", fetchImpl: async () => {} }));
});

test("assertApiPath allows only /api and /health paths", () => {
  for (const ok of ["/api", "/api/movies", "/api/movies/3", "/api/screenings/12/seats", "/health", "/health/db"]) {
    assert.doesNotThrow(() => assertApiPath(ok), ok);
  }
  for (const bad of ["", "api/movies", "/apix", "/other", "//evil.example/api", "/api//x", "/api/../x",
    "/api/./x", "/api/%2e%2e/x", "http://evil.example/api", "/api?x=1", "/api/x y", "/api\\x", null, 5]) {
    assert.throws(() => assertApiPath(bad), undefined, String(bad));
  }
});

// --- requests -----------------------------------------------------------------------

test("a GET sends Accept, no body, no cookies, and returns the parsed JSON", async () => {
  const { api, fetchImpl } = client(() => jsonResponse(200, { status: "ok" }));

  const body = await api.get("/health");

  assert.deepEqual(body, { status: "ok" });
  const { url, init } = fetchImpl.calls[0];
  assert.equal(url, "http://localhost:5000/health");
  assert.equal(init.method, "GET");
  assert.equal(init.headers.Accept, "application/json");
  assert.equal(init.credentials, "omit");
  assert.equal(init.mode, "cors");
  assert.equal(init.redirect, "error");
  assert.equal(init.cache, "no-store");
  assert.equal(init.body, undefined);
  assert.equal(init.headers["Content-Type"], undefined);
});

test("a POST sends a JSON body with the JSON content type", async () => {
  const { api, fetchImpl } = client(() => jsonResponse(201, { id: 1 }));

  assert.deepEqual(await api.post("/api/things", { a: 1, name: "값" }), { id: 1 });

  const { init } = fetchImpl.calls[0];
  assert.equal(init.method, "POST");
  assert.equal(init.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(init.body), { a: 1, name: "값" });
});

test("PUT and a bodiless POST still send a JSON object", async () => {
  const { api, fetchImpl } = client(() => jsonResponse(200, {}));

  await api.put("/api/things/1", { a: 2 });
  await api.post("/api/things/1/pay");

  assert.equal(fetchImpl.calls[0].init.method, "PUT");
  assert.equal(fetchImpl.calls[1].init.body, "{}");
});

test("query values are encoded and empty ones are dropped", async () => {
  const { api, fetchImpl } = client(() => jsonResponse(200, []));

  await api.get("/api/screenings", { query: { movie_id: 3, date: "2026-11-25", q: "a&b c", none: undefined, nil: null, blank: "" } });

  assert.equal(fetchImpl.calls[0].url, "http://localhost:5000/api/screenings?movie_id=3&date=2026-11-25&q=a%26b+c");
});

test("a 204 answer returns null", async () => {
  const { api } = client(() => new Response(null, { status: 204 }));

  assert.equal(await api.post("/api/auth/logout"), null);
});

test("the Authorization header is sent only when there is a token and auth is wanted", async () => {
  const { api, fetchImpl, storage } = client(() => jsonResponse(200, {}));
  await api.get("/api/a");
  assert.equal(fetchImpl.calls[0].init.headers.Authorization, undefined);

  api.tokenStore.set("abc.def");
  assert.equal(storage.getItem(TOKEN_KEY), "abc.def");
  await api.get("/api/a");
  await api.get("/api/a", { auth: false });

  assert.equal(fetchImpl.calls[1].init.headers.Authorization, "Bearer abc.def");
  assert.equal(fetchImpl.calls[2].init.headers.Authorization, undefined);
});

test("a request to a non-API path is refused before anything is sent", async () => {
  const { api, fetchImpl } = client(() => jsonResponse(200, {}));
  api.tokenStore.set("secret-token");

  for (const bad of ["http://evil.example/api/x", "//evil.example/api", "/static/app.js"]) {
    const error = await rejection(api.get(bad));
    assert.ok(error instanceof Error && !(error instanceof ApiError), bad);
  }
  assert.equal(fetchImpl.calls.length, 0);
});

// --- errors -------------------------------------------------------------------------

test("the error envelope becomes an ApiError with code, message and fields", async () => {
  const { api } = client(() => jsonResponse(400, { error: { code: "validation_error", message: "Fix it.", fields: { title: "Required." } } }));

  const error = await rejection(api.post("/api/admin/movies", {}));

  assert.ok(error instanceof ApiError);
  assert.equal(error.status, 400);
  assert.equal(error.code, "validation_error");
  assert.equal(error.message, "Fix it.");
  assert.deepEqual(error.fields, { title: "Required." });
});

test("an error without the envelope still becomes a usable ApiError and keeps the body", async () => {
  const { api } = client(() => jsonResponse(503, { status: "unavailable", database: "unavailable" }));

  const error = await rejection(api.get("/health/db"));

  assert.equal(error.status, 503);
  assert.equal(error.code, "http_503");
  assert.deepEqual(error.body, { status: "unavailable", database: "unavailable" });
});

test("a non-JSON error body never leaks into the message", async () => {
  const { api } = client(() => new Response("<html>Traceback: secret</html>", { status: 500 }));

  const error = await rejection(api.get("/api/x"));

  assert.equal(error.code, "http_500");
  assert.ok(!error.message.includes("secret"));
  assert.equal(error.body, null);
});

test("a 200 answer that is not JSON is reported as an invalid response", async () => {
  const { api } = client(() => new Response("<html></html>", { status: 200 }));

  assert.equal((await rejection(api.get("/api/x"))).code, "invalid_response");
});

test("an unreachable server is a network_error with status 0", async () => {
  const { api } = client(() => {
    throw new TypeError("Failed to fetch");
  });

  const error = await rejection(api.get("/api/x"));

  assert.ok(error instanceof ApiError);
  assert.equal(error.status, 0);
  assert.equal(error.code, "network_error");
});

test("a slow server is a timeout", async () => {
  const fetchImpl = (url, init) =>
    new Promise((resolve, reject) => {
      init.signal.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
    });
  const api = createApiClient({ baseUrl: BASE, fetchImpl, storage: memoryStorage(), timeoutMs: 20 });

  const error = await rejection(api.get("/api/x"));

  assert.equal(error.code, "timeout");
  assert.equal(error.status, 0);
});

// --- 401 handling -------------------------------------------------------------------

test("a 401 for a request that carried a token clears the token and notifies", async () => {
  const seen = [];
  const { api, storage } = client(
    () => jsonResponse(401, { error: { code: "unauthorized", message: "Authentication is required." } }),
    { onUnauthorized: (error) => seen.push(error.code) },
  );
  api.tokenStore.set("old.token");

  const error = await rejection(api.get("/api/bookings"));

  assert.equal(error.status, 401);
  assert.equal(storage.getItem(TOKEN_KEY), null);
  assert.deepEqual(seen, ["unauthorized"]);
});

test("a 401 without a token (for example a failed login) does not trigger the handler", async () => {
  const seen = [];
  const { api } = client(
    () => jsonResponse(401, { error: { code: "unauthorized", message: "Wrong account ID or password." } }),
    { onUnauthorized: () => seen.push(1) },
  );

  const error = await rejection(api.post("/api/auth/login", { username: "x", password: "y" }));

  assert.equal(error.code, "unauthorized");
  assert.deepEqual(seen, []);
});

test("other errors keep the token", async () => {
  const { api, storage } = client(() => jsonResponse(403, { error: { code: "forbidden", message: "No." } }));
  api.tokenStore.set("keep.me");

  await rejection(api.get("/api/admin/movies"));

  assert.equal(storage.getItem(TOKEN_KEY), "keep.me");
});

// --- storage ------------------------------------------------------------------------

test("a storage that throws does not break the client", async () => {
  const broken = {
    getItem() { throw new Error("blocked"); },
    setItem() { throw new Error("blocked"); },
    removeItem() { throw new Error("blocked"); },
  };
  const { api } = client(() => jsonResponse(200, { ok: true }), { storage: broken });

  api.tokenStore.set("x");
  assert.equal(api.tokenStore.get(), null);
  assert.doesNotThrow(() => api.tokenStore.clear());
  assert.deepEqual(await api.get("/api/x"), { ok: true });
});
