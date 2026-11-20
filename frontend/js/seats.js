// Pure helpers for seat presentation and selection state.
// All rendering uses text nodes (no innerHTML) per the project's security rules.

import { formatMoney } from "./format.js";

/** Return standard label e.g. "A1", "C10". */
export function seatLabel(seat) {
  if (!seat || !seat.seat_row || seat.seat_number == null) return "";
  return `${seat.seat_row}${seat.seat_number}`;
}

/** Parse a comma-separated query string (e.g. "1,2,3") into an array of unique positive integers. */
export function parseSelectedSeats(param) {
  if (typeof param !== "string" || !param.trim()) return [];
  const parts = param.split(",");
  const result = [];
  const seen = new Set();
  for (const part of parts) {
    const trimmed = part.trim();
    if (/^[1-9]\d*$/.test(trimmed)) {
      const id = Number(trimmed);
      if (Number.isSafeInteger(id) && !seen.has(id)) {
        seen.add(id);
        result.push(id);
      }
    }
  }
  return result;
}

/** Format an iterable of numeric seat IDs into a canonical comma-separated string sorted ascending. */
export function formatSelectedSeats(seatIds) {
  if (!seatIds) return "";
  const arr = Array.from(seatIds, Number).filter((n) => Number.isSafeInteger(n) && n > 0);
  arr.sort((a, b) => a - b);
  return arr.join(",");
}

/** Group a flat array of seats by row, preserving row order ('A'..'E') and seat number order (1..10). */
export function groupSeatsByRow(seats) {
  const rows = new Map();
  if (!Array.isArray(seats)) return rows;
  for (const seat of seats) {
    const row = seat.seat_row;
    if (!rows.has(row)) {
      rows.set(row, []);
    }
    rows.get(row).push(seat);
  }
  for (const list of rows.values()) {
    list.sort((a, b) => a.seat_number - b.seat_number);
  }
  return rows;
}

/**
 * Calculate total price as exact decimal string without floating point inaccuracies.
 * Multiplies an exact decimal string (e.g. "12000.00" or "9500.50") by an integer count.
 */
export function calculateTotal(count, ticketPrice) {
  if (!Number.isInteger(count) || count <= 0) return "0.00";
  if (typeof ticketPrice !== "string") return "0.00";

  const match = /^(\d+)(?:\.(\d+))?$/.exec(ticketPrice.trim());
  if (!match) return "0.00";

  const whole = BigInt(match[1]);
  const fracStr = (match[2] || "").slice(0, 2).padEnd(2, "0");
  const frac = BigInt(fracStr);

  const priceInCents = whole * 100n + frac;
  const totalInCents = priceInCents * BigInt(count);

  const totalWhole = totalInCents / 100n;
  const totalFrac = totalInCents % 100n;

  return `${totalWhole}.${totalFrac.toString().padStart(2, "0")}`;
}
