// Helpers shared by the admin pages (T7, T8): the administrator guard, data tables and the
// conversion of an API timestamp into the value of a datetime-local input.
// Like the rest of the frontend this builds the page with text nodes only (ui.js).

import { getAuth, loginUrl, pageUser } from "./auth.js";
import { formatDateTime } from "./format.js";
import { el, showMessage } from "./ui.js";

/**
 * Make sure an administrator is logged in. Returns the user, or null when the page must stop:
 * either the browser is being sent to the login page, or an error message has been shown.
 * The server checks the role on every request as well; this only keeps the page honest.
 *
 * `page`: the page path used for `?next=`. `messageBox`: where to explain. `hideNode`: a
 * section to hide for non-admins. `what`: "manage movies" and the like. `auth` and `navigate`
 * default to the shared auth object and a real page change; tests pass their own.
 */
export async function requireAdmin({
  page,
  messageBox,
  hideNode = null,
  what = "use this page",
  auth = getAuth(),
  navigate = (url) => globalThis.location.assign(url),
}) {
  const { user, failed } = await pageUser(auth, messageBox);
  if (failed) {
    if (hideNode) hideNode.hidden = true;
    return null; // the API cannot be reached: the message says so, no redirect
  }
  if (!user) {
    navigate(loginUrl(page));
    return null;
  }
  if (user.role !== "ADMIN") {
    if (hideNode) hideNode.hidden = true;
    showMessage(messageBox, "error", `Administrator access required. Only admins can ${what}.`);
    return null;
  }
  return user;
}

/**
 * A data table. `columns`: [{ header, cell(row) -> node | string | number | null,
 * className?, scope? }]. `rows`: the API objects. Returns a scrollable wrapper element.
 */
export function dataTable(columns, rows) {
  const head = el("tr", {}, ...columns.map((column) => el("th", { attrs: { scope: "col" } }, column.header)));
  const body = el(
    "tbody",
    {},
    ...rows.map((row) =>
      el(
        "tr",
        {},
        ...columns.map((column) => el("td", { className: column.className ?? "" }, column.cell(row) ?? "")),
      ),
    ),
  );
  return el("div", { className: "table-wrap" }, el("table", { className: "data-table" }, el("thead", {}, head), body));
}

/** "2026-11-25T19:00:00+09:00" -> "2026-11-25T19:00" (datetime-local value, as written); invalid -> "". */
export function toInputDateTime(value) {
  const text = formatDateTime(value);
  return text ? text.replace(" ", "T") : "";
}

/** A short status badge. `kind`: "ok" | "error" | "wait" | "neutral". */
export function badge(kind, text) {
  const allowed = ["ok", "error", "wait", "neutral"];
  return el("span", { className: `badge badge-${allowed.includes(kind) ? kind : "neutral"}`, text });
}

/**
 * Whether the Edit button of a screening is locked, and the tooltip that says why:
 * `{ disabled, title }`. Two rules apply, the server enforces both: a screening that has already
 * started is history, and (D2) a screening that has bookings can no longer be modified. The
 * "started" reason is shown first, matching the server's order of checks.
 */
export function screeningEditLock(screening) {
  if (screening && screening.has_started) {
    return { disabled: true, title: "This screening has already started and can't be edited." };
  }
  if (screening && screening.has_bookings) {
    return { disabled: true, title: "This screening has bookings and cannot be modified (D2)." };
  }
  return { disabled: false, title: null };
}

