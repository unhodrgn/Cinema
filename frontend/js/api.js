// API client: the ONLY place in the frontend that talks to the backend.
//
// Pages call `getApi().get("/api/...")` and receive parsed JSON or an `ApiError`. This module
// holds no business rules and no database knowledge; it knows the API's conventions
// (docs/api/api_contract.md): JSON bodies, `Authorization: Bearer <token>`, and the error
// envelope `{"error": {"code", "message", "fields"?}}`.
//
// Security properties:
//  * the token is only ever sent to the configured API origin (paths must start with /api
//    or /health; absolute URLs and `//host` forms are refused);
//  * no cookies are sent or accepted (`credentials: "omit"`); redirects are refused so the
//    Authorization header can never follow one;
//  * the token lives in sessionStorage (gone when the tab closes). It is readable by script
//    on this origin, which is why every page renders API data with textContent only (ui.js).

export const TOKEN_KEY = "cinema.token";
export const DEFAULT_TIMEOUT_MS = 10000;

export class ApiError extends Error {
  /**
   * @param {{status: number, code: string, message: string, fields?: object, body?: any}} details
   *   status 0 means the server could not be reached (code "network_error" or "timeout").
   */
  constructor({ status, code, message, fields = null, body = null }) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
    this.body = body;
  }
}

/** The canonical `scheme://host[:port]` of `value`, or throws. No path, query or wildcard. */
export function normalizeBaseUrl(value) {
  if (typeof value !== "string" || value.trim() === "" || value.includes("*")) {
    throw new Error("API base URL is not configured");
  }
  let url;
  try {
    url = new URL(value.trim());
  } catch {
    throw new Error("API base URL is not a valid URL");
  }
  const plain =
    (url.protocol === "http:" || url.protocol === "https:") &&
    (url.pathname === "/" || url.pathname === "") &&
    !url.search && !url.hash && !url.username && !url.password;
  if (!plain) {
    throw new Error("API base URL must be http(s)://host[:port] only");
  }
  return url.origin;
}

const API_PATH = /^\/(api|health)(\/[A-Za-z0-9._~!$&'()*+,;=:@%\-/]*)?$/;

/** Throws unless `path` is a plain API path such as `/api/movies/3` or `/health`. */
export function assertApiPath(path) {
  if (
    typeof path !== "string" ||
    !API_PATH.test(path) ||
    path.includes("//") ||
    path.split("/").some((part) => part === "." || part === ".." || /^%2e/i.test(part))
  ) {
    throw new Error("not an API path");
  }
}

function memoryStorage() {
  const map = new Map();
  return {
    getItem: (key) => (map.has(key) ? map.get(key) : null),
    setItem: (key, value) => void map.set(key, String(value)),
    removeItem: (key) => void map.delete(key),
  };
}

function browserStorage() {
  try {
    return globalThis.sessionStorage ?? memoryStorage();
  } catch {
    return memoryStorage(); // storage can throw (blocked site data): keep working in memory
  }
}

function buildQuery(query) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") params.append(key, String(value));
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

async function readBody(response) {
  const text = await response.text();
  if (text === "") return { empty: true };
  try {
    return { json: JSON.parse(text) };
  } catch {
    return { invalid: true };
  }
}

export function createApiClient({
  baseUrl,
  fetchImpl = globalThis.fetch?.bind(globalThis),
  storage = browserStorage(),
  timeoutMs = DEFAULT_TIMEOUT_MS,
  onUnauthorized = null,
} = {}) {
  const origin = normalizeBaseUrl(baseUrl);
  if (typeof fetchImpl !== "function") throw new Error("fetch is not available");

  const tokenStore = {
    get() {
      try {
        return storage.getItem(TOKEN_KEY);
      } catch {
        return null;
      }
    },
    set(token) {
      try {
        storage.setItem(TOKEN_KEY, token);
      } catch {
        /* the session simply will not survive a reload */
      }
    },
    clear() {
      try {
        storage.removeItem(TOKEN_KEY);
      } catch {
        /* nothing to clear */
      }
    },
  };

  async function request(method, path, { body, query, auth = true } = {}) {
    assertApiPath(path);
    const headers = { Accept: "application/json" };
    const token = auth ? tokenStore.get() : null;
    if (token) headers.Authorization = `Bearer ${token}`;
    const init = {
      method,
      headers,
      mode: "cors",
      credentials: "omit",
      cache: "no-store",
      redirect: "error",
    };
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }

    const controller = new AbortController();
    init.signal = controller.signal;
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    let response;
    let payload;
    try {
      response = await fetchImpl(origin + path + buildQuery(query), init);
      payload = await readBody(response);
    } catch (error) {
      const timedOut = controller.signal.aborted;
      throw new ApiError({
        status: 0,
        code: timedOut ? "timeout" : "network_error",
        message: timedOut
          ? "The server took too long to answer."
          : "The server cannot be reached. Please check that it is running.",
      });
    } finally {
      clearTimeout(timer);
    }

    if (response.ok) {
      if (payload.invalid) {
        throw new ApiError({ status: response.status, code: "invalid_response",
          message: "The server sent an unexpected answer." });
      }
      return payload.empty ? null : payload.json;
    }

    const envelope = payload.json?.error;
    const error = new ApiError({
      status: response.status,
      code: typeof envelope?.code === "string" ? envelope.code : `http_${response.status}`,
      message: typeof envelope?.message === "string"
        ? envelope.message
        : `The request failed (HTTP ${response.status}).`,
      fields: envelope && typeof envelope.fields === "object" ? envelope.fields : null,
      body: payload.json ?? null,
    });
    if (response.status === 401 && token) {
      tokenStore.clear(); // the token is no longer good; never keep sending it
      if (onUnauthorized) onUnauthorized(error);
    }
    throw error;
  }

  return {
    baseUrl: origin,
    tokenStore,
    request,
    get: (path, options) => request("GET", path, options),
    post: (path, body, options) => request("POST", path, { ...options, body: body ?? {} }),
    put: (path, body, options) => request("PUT", path, { ...options, body: body ?? {} }),
  };
}

let defaultClient = null;
let unauthorizedHandler = null;

/**
 * Register what happens when the shared client gets a 401 for a request that carried a
 * token (auth.js redirects to the login page). Can be set before or after `getApi()`.
 */
export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = typeof handler === "function" ? handler : null;
}

/** The shared client, configured by the server-generated /config.js (window.APP_CONFIG). */
export function getApi(options = {}) {
  if (defaultClient === null) {
    defaultClient = createApiClient({
      baseUrl: globalThis.APP_CONFIG?.apiBaseUrl,
      onUnauthorized: (error) => unauthorizedHandler?.(error),
      ...options,
    });
  }
  return defaultClient;
}
