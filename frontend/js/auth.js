// Authentication for the frontend: log in, register, log out, who am I, and the redirect to
// the login page. The server decides everything; this module only calls the API and keeps
// the token in sessionStorage (through api.js). It contains no business rules.
//
// Flow of a protected page: the page calls the API; if the token is missing or no longer good
// the API answers 401, api.js clears the token and calls `handleUnauthorized`, which sends the
// browser to /login.html?next=<this page>. After login the browser returns to `next`, but only
// if it is one of the known pages below.

import { getApi, setUnauthorizedHandler } from "./api.js";
import { describeError, showMessage } from "./ui.js";

export const LOGIN_PAGE = "/login.html";
export const REGISTER_PAGE = "/register.html";

// The only pages a login may send the browser back to. Each task that adds a page adds it
// here; anything else (another site, an unknown path, the login page itself) becomes "/".
export const ALLOWED_NEXT_PAGES = new Set([
  "/",
  "/index.html",
  "/movies.html",
  "/movie.html",
  "/screenings.html",
  "/seats.html",
  "/booking.html",
  "/bookings.html",
  "/admin-movies.html",
  "/admin-screenings.html",
  "/admin-bookings.html",
]);

const SAFE_QUERY = /^[A-Za-z0-9_=&.\-%]*$/;
const MAX_NEXT_LENGTH = 200;

/**
 * A safe same-site destination for `?next=`: a known page, optionally with a plain query
 * string. Never an absolute URL, `//host`, a backslash form, a control character, a script
 * URL or an unknown path. Returns `fallback` for anything else.
 *
 * The path must equal an allow-listed page EXACTLY (no URL parsing, no dot-segment or
 * percent-decoding tricks); a query string with any character outside letters, digits and
 * `_ = & . - %` is dropped; the fragment is dropped.
 */
export function safeNext(value, fallback = "/") {
  if (typeof value !== "string" || value.length > MAX_NEXT_LENGTH) return fallback;
  if (!value.startsWith("/") || value.startsWith("//") || /[\\\u0000-\u001f\u007f]/.test(value)) {
    return fallback;
  }
  const withoutFragment = value.split("#", 1)[0];
  const queryStart = withoutFragment.indexOf("?");
  const path = queryStart === -1 ? withoutFragment : withoutFragment.slice(0, queryStart);
  const query = queryStart === -1 ? "" : withoutFragment.slice(queryStart + 1);
  if (!ALLOWED_NEXT_PAGES.has(path)) return fallback;
  return query && SAFE_QUERY.test(query) ? `${path}?${query}` : path;
}

/** `/login.html` with a `next` parameter when the destination is something other than home. */
export function loginUrl(next) {
  const destination = safeNext(next);
  return destination === "/" ? LOGIN_PAGE : `${LOGIN_PAGE}?next=${encodeURIComponent(destination)}`;
}

export function createAuth({
  api,
  navigate = (url) => globalThis.location.assign(url),
  here = () => globalThis.location.pathname + globalThis.location.search,
} = {}) {
  let cachedUser;

  /** Log in; keeps the token for this browser tab and returns the user. */
  async function login(username, password) {
    const body = await api.post("/api/auth/login", { username, password }, { auth: false });
    api.tokenStore.set(body.token);
    cachedUser = body.user;
    return body.user;
  }

  /** Create a CUSTOMER account (the server assigns the role). Does not log in. */
  async function register(username, password) {
    const body = await api.post("/api/auth/register", { username, password }, { auth: false });
    return body.user;
  }

  /**
   * Remove the token from this tab first, so the user is logged out locally even if the
   * server cannot be reached; then tell the server (it has nothing to revoke, see the API
   * contract: a stolen token stays valid until it expires).
   */
  async function logout() {
    api.tokenStore.clear();
    cachedUser = null;
    try {
      await api.post("/api/auth/logout", {}, { auth: false });
    } catch {
      /* already logged out locally */
    }
  }

  /** The logged-in user (asked from the server), or null. Rethrows network/server errors. */
  async function currentUser({ refresh = false } = {}) {
    if (!api.tokenStore.get()) {
      cachedUser = null;
      return null;
    }
    if (cachedUser && !refresh) return cachedUser;
    try {
      cachedUser = (await api.get("/api/auth/me")).user;
    } catch (error) {
      if (error.status === 401) {
        cachedUser = null;
        return null;
      }
      throw error;
    }
    return cachedUser;
  }

  /** Called by api.js on a 401 that carried a token: back to the login page. */
  function handleUnauthorized() {
    const current = here();
    const path = current.split("?")[0];
    if (path === LOGIN_PAGE || path === REGISTER_PAGE) return; // no redirect loop
    navigate(loginUrl(current));
  }

  return { login, register, logout, currentUser, handleUnauthorized };
}

/**
 * The user for a page that needs a login: `{ user, failed }`.
 *  - no token or a 401 -> `{ user: null, failed: false }`: the caller sends the browser to login;
 *  - the API cannot be reached (or answers 5xx) -> the reason is shown in `messageBox` (when one
 *    is given) and `{ user: null, failed: true }`: the caller just stops. Not knowing who the user is must never
 *    look like "logged out", so there is no redirect and the token is kept.
 */
export async function pageUser(auth, messageBox) {
  try {
    return { user: await auth.currentUser(), failed: false };
  } catch (error) {
    if (messageBox) showMessage(messageBox, "error", describeError(error));
    return { user: null, failed: true };
  }
}

let sharedAuth = null;

/** The shared instance for the page, wired to the shared API client. */
export function getAuth() {
  if (sharedAuth === null) {
    sharedAuth = createAuth({ api: getApi() });
    setUnauthorizedHandler(sharedAuth.handleUnauthorized);
  }
  return sharedAuth;
}
