// The payment countdown and what happens when it reaches zero. Pure logic with injectable
// clock/timers so it can be tested; booking.js wires it to the page.
//
// The server decides whether a booking has expired (it expires it on the next request). So when
// the countdown ends the page does not guess: it asks the API again and shows what came back.

const OPEN = (booking) => Boolean(booking) && booking.status === "BOOKED" && booking.payment_status === "UNPAID";

/** "Time remaining: 3m 05s" for a number of milliseconds. */
export function countdownText(remainingMs) {
  const totalSec = Math.max(0, Math.floor(remainingMs / 1000));
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `Time remaining: ${min}m ${sec < 10 ? "0" : ""}${sec}s`;
}

/**
 * Tick every second until `expiresAtIso`, then call `onElapsed` exactly once and stop.
 * `onTick(text)` is called with the remaining time (also once immediately). An unparsable
 * timestamp does nothing. Returns `{ stop }`.
 */
export function createCountdown({
  expiresAtIso,
  onTick,
  onElapsed,
  now = () => Date.now(),
  setIntervalFn = (fn, ms) => globalThis.setInterval(fn, ms),
  clearIntervalFn = (id) => globalThis.clearInterval(id),
}) {
  const expiresMs = Date.parse(expiresAtIso);
  let timer = null;
  let elapsed = false;

  function stop() {
    if (timer !== null) {
      clearIntervalFn(timer);
      timer = null;
    }
  }

  function update() {
    const remaining = expiresMs - now();
    if (remaining <= 0) {
      stop();
      if (!elapsed) {
        elapsed = true;
        onElapsed();
      }
      return;
    }
    onTick(countdownText(remaining));
  }

  if (!Number.isNaN(expiresMs)) {
    update();
    if (!elapsed) timer = setIntervalFn(update, 1000);
  }
  return { stop };
}

/**
 * After the deadline: load the booking until the server no longer reports it as open
 * (BOOKED and UNPAID). The browser clock can run a little ahead of the server's, so the first
 * answers may still say "open"; try up to `maxTries` times, `delayMs` apart.
 * `reload()` returns the booking (or null when it could not be loaded); `wait(ms)` sleeps.
 * Returns the last booking seen, and whether it is still open.
 */
export async function confirmExpiry({ reload, wait, maxTries = 5, delayMs = 2000 }) {
  let booking = null;
  for (let attempt = 1; attempt <= maxTries; attempt += 1) {
    booking = await reload();
    if (!OPEN(booking)) return { booking, stillOpen: OPEN(booking) };
    if (attempt < maxTries) await wait(delayMs);
  }
  return { booking, stillOpen: OPEN(booking) };
}
