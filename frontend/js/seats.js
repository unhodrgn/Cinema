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

/**
 * Take every seat that is no longer free out of `selected` (a Set of seat ids) after the seat map
 * was reloaded. A selected seat that is missing from the map counts as gone too. Returns the
 * labels of the seats that were removed (sorted by row, then number), e.g. ["D5"].
 */
export function dropUnavailable(selected, seats) {
  const bySeat = new Map((Array.isArray(seats) ? seats : []).map((seat) => [seat.seat_id, seat]));
  const removed = [];
  for (const id of Array.from(selected)) {
    const seat = bySeat.get(id);
    if (seat && seat.is_available) continue;
    selected.delete(id);
    if (seat) removed.push(seat);
  }
  removed.sort((a, b) => a.seat_row.localeCompare(b.seat_row) || a.seat_number - b.seat_number);
  return removed.map(seatLabel);
}

/** The sentence shown when seats of the selection were taken by someone else ("" for none). */
export function takenSeatsMessage(labels) {
  if (!Array.isArray(labels) || labels.length === 0) return "";
  const what = labels.length === 1 ? `Seat ${labels[0]} was` : `Seats ${labels.join(", ")} were`;
  return `${what} just taken by someone else and removed from your selection. Please choose another seat.`;
}

