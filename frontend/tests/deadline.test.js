// Tests for js/deadline.js. Run: node --test tests/deadline.test.js (from frontend/)

import assert from "node:assert/strict";
import { test } from "node:test";

import { confirmExpiry, countdownText, createCountdown } from "../js/deadline.js";

test("countdownText shows minutes and zero-padded seconds, never negative", () => {
  assert.equal(countdownText(10 * 60 * 1000), "Time remaining: 10m 00s");
  assert.equal(countdownText(185_000), "Time remaining: 3m 05s");
  assert.equal(countdownText(999), "Time remaining: 0m 00s");
  assert.equal(countdownText(-5000), "Time remaining: 0m 00s");
});

function fakeClock(startMs) {
  const clock = { t: startMs, id: 0, fn: null, cleared: 0 };
  clock.now = () => clock.t;
  clock.setIntervalFn = (fn) => { clock.fn = fn; clock.id += 1; return clock.id; };
  clock.clearIntervalFn = () => { clock.fn = null; clock.cleared += 1; };
  clock.advance = (ms) => { clock.t += ms; if (clock.fn) clock.fn(); };
  return clock;
}

test("the countdown ticks until the deadline, then calls onElapsed exactly once and stops", () => {
  const clock = fakeClock(Date.parse("2026-11-23T20:30:00Z"));
  const ticks = [];
  let elapsed = 0;
  createCountdown({
    expiresAtIso: "2026-11-23T20:30:03Z",
    onTick: (text) => ticks.push(text), onElapsed: () => { elapsed += 1; },
    now: clock.now, setIntervalFn: clock.setIntervalFn, clearIntervalFn: clock.clearIntervalFn,
  });
  assert.deepEqual(ticks, ["Time remaining: 0m 03s"]);
  clock.advance(1000);
  clock.advance(1000);
  assert.deepEqual(ticks, ["Time remaining: 0m 03s", "Time remaining: 0m 02s", "Time remaining: 0m 01s"]);
  assert.equal(elapsed, 0);
  clock.advance(1000);
  assert.equal(elapsed, 1);
  assert.equal(clock.fn, null); // the interval was cleared
  assert.equal(ticks.length, 3);
});

test("a deadline that has already passed calls onElapsed at once and starts no timer", () => {
  const clock = fakeClock(Date.parse("2026-11-23T21:00:00Z"));
  let elapsed = 0;
  createCountdown({
    expiresAtIso: "2026-11-23T20:30:00Z", onTick: () => assert.fail("no tick"), onElapsed: () => { elapsed += 1; },
    now: clock.now, setIntervalFn: clock.setIntervalFn, clearIntervalFn: clock.clearIntervalFn,
  });
  assert.equal(elapsed, 1);
  assert.equal(clock.fn, null);
});

test("stop() cancels the countdown and an unparsable deadline does nothing", () => {
  const clock = fakeClock(0);
  let elapsed = 0;
  const handle = createCountdown({
    expiresAtIso: "1970-01-01T00:00:10Z", onTick: () => {}, onElapsed: () => { elapsed += 1; },
    now: clock.now, setIntervalFn: clock.setIntervalFn, clearIntervalFn: clock.clearIntervalFn,
  });
  handle.stop();
  assert.equal(clock.fn, null);
  assert.equal(elapsed, 0);

  const none = createCountdown({ expiresAtIso: "nonsense", onTick: () => assert.fail(), onElapsed: () => assert.fail(),
    now: clock.now, setIntervalFn: clock.setIntervalFn, clearIntervalFn: clock.clearIntervalFn });
  none.stop();
});

const OPEN = { status: "BOOKED", payment_status: "UNPAID" };
const EXPIRED = { status: "EXPIRED", payment_status: "UNPAID" };

test("confirmExpiry returns the expired booking as soon as the server reports it", async () => {
  let calls = 0;
  const waits = [];
  const result = await confirmExpiry({ reload: async () => { calls += 1; return EXPIRED; }, wait: async (ms) => waits.push(ms) });
  assert.deepEqual(result, { booking: EXPIRED, stillOpen: false });
  assert.equal(calls, 1);
  assert.deepEqual(waits, []);
});

test("confirmExpiry retries while the server still says open (clock skew), then accepts EXPIRED", async () => {
  const answers = [OPEN, OPEN, EXPIRED];
  const waits = [];
  const result = await confirmExpiry({ reload: async () => answers.shift(), wait: async (ms) => waits.push(ms), delayMs: 1500 });
  assert.equal(result.booking, EXPIRED);
  assert.equal(result.stillOpen, false);
  assert.deepEqual(waits, [1500, 1500]);
});

test("confirmExpiry gives up after maxTries and reports the booking as still open", async () => {
  let calls = 0;
  const result = await confirmExpiry({ reload: async () => { calls += 1; return OPEN; }, wait: async () => {}, maxTries: 3 });
  assert.equal(calls, 3);
  assert.equal(result.stillOpen, true);
});

test("confirmExpiry stops at once for a paid or cancelled booking and for a load failure", async () => {
  const paid = { status: "BOOKED", payment_status: "PAID" };
  assert.equal((await confirmExpiry({ reload: async () => paid, wait: async () => {} })).stillOpen, false);
  const failed = await confirmExpiry({ reload: async () => null, wait: async () => assert.fail("no wait") });
  assert.deepEqual(failed, { booking: null, stillOpen: false });
});
