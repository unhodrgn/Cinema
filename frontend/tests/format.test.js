// Tests for js/format.js. Run: node --test tests/format.test.js (from frontend/)

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  formatDate, formatDateTime, formatDateTimeRange, formatDuration, formatMoney, formatTime, formatTimeRange,
  isDateText, isIdText,
} from "../js/format.js";

test("money keeps the decimal string exact and groups thousands", () => {
  const cases = {
    "12000.00": "₩12,000", "9500.50": "₩9,500.50", "0.00": "₩0", "0": "₩0", "0.5": "₩0.5", "999.99": "₩999.99",
    "1000": "₩1,000", "1234567.80": "₩1,234,567.80", "99999999.99": "₩99,999,999.99", "-5.25": "-₩5.25",
    " 12000.00 ": "₩12,000",
  };
  for (const [input, expected] of Object.entries(cases)) assert.equal(formatMoney(input), expected, input);
});

test("money never goes through floating point", () => {
  assert.equal(formatMoney("0.1"), "₩0.1");
  assert.equal(formatMoney("9007199254740993.01"), "₩9,007,199,254,740,993.01"); // beyond 2**53
  assert.equal(formatMoney("12345678901234567890.10"), "₩12,345,678,901,234,567,890.10");
});

test("money refuses anything that is not a plain decimal string", () => {
  for (const bad of ["", "abc", "12,000", "1e3", "NaN", "Infinity", "--1", "1.", ".5", "1 2", null, undefined, 12000,
    {}, [], "12000.00; DROP", "<b>1</b>"]) {
    assert.equal(formatMoney(bad), "", String(bad));
  }
});

test("times are shown exactly as the API wrote them, in the cinema's own offset", () => {
  assert.equal(formatDateTime("2026-11-25T19:00:00+09:00"), "2026-11-25 19:00");
  assert.equal(formatDate("2026-11-25T19:00:00+09:00"), "2026-11-25");
  assert.equal(formatTime("2026-11-25T19:00:00+09:00"), "19:00");
  assert.equal(formatDateTime("2030-03-15T00:00:00+09:00"), "2030-03-15 00:00");
  assert.equal(formatDateTime("2030-03-15T23:59:59.123456+09:00"), "2030-03-15 23:59");
  assert.equal(formatTimeRange("2026-11-25T19:00:00+09:00", "2026-11-25T21:05:00+09:00"), "19:00 - 21:05");
  assert.equal(formatTimeRange("2026-11-25T19:00:00+09:00", ""), "19:00");
});

test("the displayed time does not depend on the browser's time zone", () => {
  const iso = "2026-11-25T19:00:00+09:00";
  const before = formatDateTime(iso);
  for (const zone of ["UTC", "America/New_York", "Asia/Seoul", "Pacific/Kiritimati", "Europe/London"]) {
    process.env.TZ = zone;
    assert.equal(formatDateTime(iso), before, zone);
    assert.equal(formatTime(iso), "19:00", zone);
  }
});

test("time formatting refuses anything that is not an ISO timestamp", () => {
  for (const bad of ["", "tomorrow", "2026-11-25", "19:00", "2026-11-25 19:00", null, undefined, 5, {}, "<script>"]) {
    assert.equal(formatDateTime(bad), "", String(bad));
    assert.equal(formatDate(bad), "", String(bad));
    assert.equal(formatTime(bad), "", String(bad));
  }
});

test("running time", () => {
  assert.equal(formatDuration(120), "120 min");
  for (const bad of [0, -1, 1.5, "120", null, undefined, NaN]) assert.equal(formatDuration(bad), "", String(bad));
});

test("id and date text checks accept only the plain shapes", () => {
  for (const ok of ["1", "42", "9223372036854775807"]) assert.ok(isIdText(ok), ok);
  for (const bad of ["0", "01", "-1", "1.5", "1e3", "", " 1", "1 ", "abc", "1;2", "99999999999999999999", null, 3, undefined]) {
    assert.ok(!isIdText(bad), String(bad));
  }
  assert.ok(isDateText("2026-11-25") && isDateText("0000-00-00"));
  for (const bad of ["2026-1-25", "20261125", "2026-11-25T10:00", "", null, undefined, 5, "26-11-25"]) {
    assert.ok(!isDateText(bad), String(bad));
  }
});

test("a date-and-time range shows the date once, and both dates when the end is on another day", () => {
  const start = "2026-11-25T19:00:00+09:00";
  assert.equal(formatDateTimeRange(start, "2026-11-25T21:05:00+09:00"), "2026-11-25 19:00 - 21:05");
  assert.equal(formatDateTimeRange("2026-11-25T23:30:00+09:00", "2026-11-26T01:10:00+09:00"),
    "2026-11-25 23:30 - 2026-11-26 01:10");
  assert.equal(formatDateTimeRange(start, ""), "2026-11-25 19:00");
  assert.equal(formatDateTimeRange(start, undefined), "2026-11-25 19:00");
  assert.equal(formatDateTimeRange("", "2026-11-25T21:05:00+09:00"), "");
  assert.equal(formatDateTimeRange(null, null), "");
});
