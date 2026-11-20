// Tests for js/admin.js and js/admin_bookings.js (T7, T8) with a minimal fake DOM.
// Run: node --test tests/admin.test.js (from frontend/)

import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { badge, dataTable, requireAdmin, toInputDateTime } from "../js/admin.js";
import {
  BOOKING_STATUSES,
  bookingColumns,
  bookingTimeline,
  paymentKind,
  readFilters,
  seatsText,
  statusKind,
} from "../js/admin_bookings.js";

class FakeNode {
  constructor(tag) {
    this.tag = tag;
    this.attributes = {};
    this.children = [];
    this.className = "";
    this.hidden = false;
    this._text = "";
  }
  set innerHTML(value) { throw new Error("innerHTML must not be used"); }
  set outerHTML(value) { throw new Error("outerHTML must not be used"); }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(""); }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener() {}
  replaceChildren() { this.children = []; this._text = ""; }
  append(...nodes) { this.children.push(...nodes); }
  all(tag) {
    const found = [];
    for (const child of this.children) {
      if (child.tag === tag) found.push(child);
      if (child.all) found.push(...child.all(tag));
    }
    return found;
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

const HOSTILE = '<img src=x onerror=alert(1)><script>alert(2)</script>';

// --- admin.js ---------------------------------------------------------------------------------

test("toInputDateTime turns an API timestamp into a datetime-local value, as written", () => {
  assert.equal(toInputDateTime("2026-11-25T19:00:00+09:00"), "2026-11-25T19:00");
  assert.equal(toInputDateTime("2026-11-25T19:05:30Z"), "2026-11-25T19:05");
  for (const bad of ["", "nope", null, undefined, 5, "2026-11-25"]) assert.equal(toInputDateTime(bad), "", String(bad));
});

test("badge uses the requested kind and falls back to neutral", () => {
  assert.equal(badge("ok", "Paid").className, "badge badge-ok");
  assert.equal(badge("wait", "Unpaid").className, "badge badge-wait");
  assert.equal(badge("error", "x").className, "badge badge-error");
  assert.equal(badge("evil badge-ok", "x").className, "badge badge-neutral");
  assert.equal(badge("ok", "Paid").textContent, "Paid");
});

test("dataTable builds a header, one row per item and one cell per column", () => {
  const rows = [{ id: 1, name: "A" }, { id: 2, name: "B" }, { id: 3, name: "C" }];
  const wrapper = dataTable(
    [
      { header: "ID", cell: (r) => String(r.id) },
      { header: "Name", className: "cell-strong", cell: (r) => r.name },
    ],
    rows,
  );
  assert.equal(wrapper.className, "table-wrap");
  const [table] = wrapper.all("table");
  assert.equal(table.className, "data-table");
  assert.deepEqual(wrapper.all("th").map((th) => th.textContent), ["ID", "Name"]);
  assert.ok(wrapper.all("th").every((th) => th.attributes.scope === "col"));
  assert.equal(wrapper.all("tr").length, 4); // header + 3 rows
  const cells = wrapper.all("td");
  assert.equal(cells.length, 6);
  assert.deepEqual(cells.map((td) => td.textContent), ["1", "A", "2", "B", "3", "C"]);
  assert.equal(cells[1].className, "cell-strong");
});

test("dataTable shows null cells as empty and API text only as text", () => {
  const wrapper = dataTable(
    [{ header: "Title", cell: (r) => r.title }, { header: "Missing", cell: () => null }],
    [{ title: HOSTILE }],
  );
  const cells = wrapper.all("td");
  assert.equal(cells[0].textContent, HOSTILE);
  assert.equal(cells[0].children.length, 1); // one text node, no parsed elements
  assert.equal(cells[1].textContent, "");
  assert.equal(wrapper.all("img").length + wrapper.all("script").length, 0);
});

test("dataTable with no rows still has its header", () => {
  const wrapper = dataTable([{ header: "ID", cell: (r) => r.id }], []);
  assert.equal(wrapper.all("th").length, 1);
  assert.equal(wrapper.all("td").length, 0);
});

function fakeAuth(result) {
  return { currentUser: async () => { if (result instanceof Error) throw result; return result; } };
}

test("requireAdmin returns the user for an administrator", async () => {
  const user = { user_id: 1, username: "root", role: "ADMIN" };
  const navigations = [];
  const box = new FakeNode("div");
  const got = await requireAdmin({ page: "/admin-movies.html", messageBox: box, auth: fakeAuth(user), navigate: (u) => navigations.push(u) });
  assert.equal(got, user);
  assert.deepEqual(navigations, []);
  assert.equal(box.textContent, "");
});

test("requireAdmin sends a logged-out visitor to the login page and then to the same page", async () => {
  const navigations = [];
  const got = await requireAdmin({ page: "/admin-bookings.html", messageBox: new FakeNode("div"), auth: fakeAuth(null), navigate: (u) => navigations.push(u) });
  assert.equal(got, null);
  assert.deepEqual(navigations, ["/login.html?next=%2Fadmin-bookings.html"]);
});

test("requireAdmin treats an unreachable API like a logged-out visitor", async () => {
  const navigations = [];
  const got = await requireAdmin({ page: "/admin-movies.html", messageBox: new FakeNode("div"), auth: fakeAuth(new Error("network")), navigate: (u) => navigations.push(u) });
  assert.equal(got, null);
  assert.equal(navigations.length, 1);
});

test("requireAdmin refuses a customer: message shown, form hidden, no redirect", async () => {
  const navigations = [];
  const box = new FakeNode("div");
  const form = new FakeNode("section");
  const got = await requireAdmin({
    page: "/admin-movies.html", messageBox: box, hideNode: form, what: "manage movies",
    auth: fakeAuth({ user_id: 2, username: "alice", role: "CUSTOMER" }), navigate: (u) => navigations.push(u),
  });
  assert.equal(got, null);
  assert.equal(form.hidden, true);
  assert.deepEqual(navigations, []);
  assert.match(box.textContent, /Administrator access required\. Only admins can manage movies\./);
});

// --- admin_bookings.js ------------------------------------------------------------------------

test("status and payment badges use the same colours as the customer pages", () => {
  assert.equal(statusKind("BOOKED"), "ok");
  assert.equal(statusKind("EXPIRED"), "error");
  assert.equal(statusKind("CANCELLED"), "neutral");
  assert.equal(statusKind("whatever"), "neutral");
  assert.equal(paymentKind("PAID"), "ok");
  assert.equal(paymentKind("UNPAID"), "wait");
  assert.deepEqual(BOOKING_STATUSES, ["BOOKED", "CANCELLED", "EXPIRED"]);
});

test("seatsText lists the seats of a booking and says Released once they were given back", () => {
  const seats = [{ seat_row: "B", seat_number: 3 }, { seat_row: "B", seat_number: 4 }];
  assert.equal(seatsText({ status: "BOOKED", seats }), "B3, B4");
  assert.equal(seatsText({ status: "BOOKED", seats: [] }), "-");
  assert.equal(seatsText({ status: "CANCELLED", seats: [] }), "Released");
  assert.equal(seatsText({ status: "EXPIRED" }), "Released");
  assert.equal(seatsText(null), "");
});

test("bookingTimeline says what happened last, with times as the API wrote them", () => {
  const base = { expires_at: "2026-11-25T19:10:00+09:00", paid_at: null, cancelled_at: null };
  assert.equal(bookingTimeline({ ...base, status: "BOOKED", payment_status: "UNPAID" }), "Pay by 2026-11-25 19:10");
  assert.equal(bookingTimeline({ ...base, status: "BOOKED", payment_status: "PAID", paid_at: "2026-11-25T19:05:00+09:00" }), "Paid 2026-11-25 19:05");
  assert.equal(bookingTimeline({ ...base, status: "CANCELLED", payment_status: "UNPAID", cancelled_at: "2026-11-25T19:02:00+09:00" }), "Cancelled 2026-11-25 19:02");
  assert.equal(bookingTimeline({ ...base, status: "EXPIRED", payment_status: "UNPAID" }), "Expired (window ended 2026-11-25 19:10)");
  assert.equal(bookingTimeline(null), "");
});

test("readFilters keeps only the filled-in, valid filters", () => {
  assert.deepEqual(readFilters({}), { query: {}, problems: {} });
  assert.deepEqual(readFilters({ status: "booked", screeningId: " 12 ", userId: "7" }),
    { query: { status: "BOOKED", screening_id: "12", user_id: "7" }, problems: {} });
  assert.deepEqual(readFilters({ status: "", screeningId: "", userId: "  " }), { query: {}, problems: {} });
});

test("readFilters reports every bad filter and leaves it out of the query", () => {
  const { query, problems } = readFilters({ status: "PAID", screeningId: "abc", userId: "0" });
  assert.deepEqual(query, {});
  assert.deepEqual(Object.keys(problems).sort(), ["screening_id", "status", "user_id"]);
  for (const bad of ["-1", "1.5", "03", "1e3", "99999999999999999999"]) {
    assert.ok(readFilters({ screeningId: bad }).problems.screening_id, bad);
  }
});

test("the booking table shows one row per booking with every column", () => {
  const booking = {
    booking_id: 9, user_id: 4, username: "alice", showtime_id: 21, title: "Phim 1", room_name: "Room 2",
    starts_at: "2026-11-25T19:00:00+09:00", ends_at: "2026-11-25T21:00:00+09:00", total_amount: "28000.00",
    status: "BOOKED", payment_status: "UNPAID", booked_at: "2026-11-25T18:00:00+09:00",
    expires_at: "2026-11-25T18:10:00+09:00", paid_at: null, cancelled_at: null,
    seats: [{ seat_row: "A", seat_number: 1 }, { seat_row: "A", seat_number: 2 }],
  };
  const columns = bookingColumns();
  assert.deepEqual(columns.map((c) => c.header),
    ["Booking", "Customer", "Movie", "Screening", "Seats", "Total", "Status", "Booked", "Last event"]);
  const wrapper = dataTable(columns, [booking]);
  assert.deepEqual(wrapper.all("td").map((td) => td.textContent), [
    "#9", "alice (#4)", "Phim 1", "#21 · Room 2 · 2026-11-25 19:00", "A1, A2", "28,000",
    "BOOKEDUNPAID", "2026-11-25 18:00", "Pay by 2026-11-25 18:10",
  ]);
});

test("the booking table renders hostile customer and movie text as plain text", () => {
  const booking = {
    booking_id: 1, user_id: 1, username: HOSTILE, showtime_id: 1, title: HOSTILE, room_name: HOSTILE,
    starts_at: "2026-11-25T19:00:00+09:00", total_amount: "1.00", status: "CANCELLED", payment_status: "UNPAID",
    booked_at: "2026-11-25T18:00:00+09:00", expires_at: "2026-11-25T18:10:00+09:00", cancelled_at: "2026-11-25T18:01:00+09:00", seats: [],
  };
  const wrapper = dataTable(bookingColumns(), [booking]);
  assert.equal(wrapper.all("img").length + wrapper.all("script").length, 0);
  assert.ok(wrapper.all("td")[1].textContent.includes(HOSTILE));
});
