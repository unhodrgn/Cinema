import assert from "node:assert/strict";
import { test } from "node:test";

import {
  calculateTotal,
  dropUnavailable,
  formatSelectedSeats,
  groupSeatsByRow,
  parseSelectedSeats,
  seatLabel,
  takenSeatsMessage,
} from "../js/seats.js";

test("seatLabel builds correct row and number text", () => {
  assert.equal(seatLabel({ seat_row: "A", seat_number: 1 }), "A1");
  assert.equal(seatLabel({ seat_row: "C", seat_number: 10 }), "C10");
  assert.equal(seatLabel(null), "");
  assert.equal(seatLabel({}), "");
});

test("parseSelectedSeats parses valid integers and drops duplicates/garbage", () => {
  assert.deepEqual(parseSelectedSeats("1,2,3"), [1, 2, 3]);
  assert.deepEqual(parseSelectedSeats(" 5 , 10 , 5 "), [5, 10]);
  assert.deepEqual(parseSelectedSeats("abc,-1,0,999"), [999]);
  assert.deepEqual(parseSelectedSeats(""), []);
  assert.deepEqual(parseSelectedSeats(null), []);
});

test("formatSelectedSeats sorts and joins with comma", () => {
  assert.equal(formatSelectedSeats([3, 1, 2]), "1,2,3");
  assert.equal(formatSelectedSeats(new Set([10, 5])), "5,10");
  assert.equal(formatSelectedSeats([]), "");
  assert.equal(formatSelectedSeats(null), "");
});

test("groupSeatsByRow groups seats into sorted rows", () => {
  const seats = [
    { seat_id: 2, seat_row: "A", seat_number: 2 },
    { seat_id: 1, seat_row: "A", seat_number: 1 },
    { seat_id: 11, seat_row: "B", seat_number: 1 },
  ];
  const grouped = groupSeatsByRow(seats);
  assert.equal(grouped.size, 2);
  assert.deepEqual(grouped.get("A").map((s) => s.seat_number), [1, 2]);
  assert.deepEqual(grouped.get("B").map((s) => s.seat_number), [1]);
});

test("calculateTotal multiplies exact decimal without float loss", () => {
  assert.equal(calculateTotal(1, "12000.00"), "12000.00");
  assert.equal(calculateTotal(3, "12000.00"), "36000.00");
  assert.equal(calculateTotal(2, "9500.50"), "19001.00");
  assert.equal(calculateTotal(0, "12000.00"), "0.00");
  assert.equal(calculateTotal(2, "bad"), "0.00");
});

const SEATS = [
  { seat_id: 1, seat_row: "A", seat_number: 1, is_available: true },
  { seat_id: 2, seat_row: "A", seat_number: 2, is_available: true },
  { seat_id: 15, seat_row: "B", seat_number: 5, is_available: false },
  { seat_id: 4, seat_row: "A", seat_number: 4, is_available: false },
];

test("dropUnavailable removes the seats that were taken and keeps the free ones", () => {
  const selected = new Set([1, 15, 2, 4]);
  const removed = dropUnavailable(selected, SEATS);
  assert.deepEqual(removed, ["A4", "B5"]); // sorted by row, then number
  assert.deepEqual([...selected].sort(), [1, 2]);
});

test("dropUnavailable leaves a fully free selection alone and treats an unknown seat as gone", () => {
  const selected = new Set([1, 2]);
  assert.deepEqual(dropUnavailable(selected, SEATS), []);
  assert.deepEqual([...selected], [1, 2]);

  const withUnknown = new Set([1, 999]);
  assert.deepEqual(dropUnavailable(withUnknown, SEATS), []); // nothing to name, but the id is dropped
  assert.deepEqual([...withUnknown], [1]);
  assert.deepEqual(dropUnavailable(new Set([1]), null), []);
});

test("after dropping, the total is recalculated from what is left", () => {
  const selected = new Set([1, 2, 15]);
  dropUnavailable(selected, SEATS);
  assert.equal(calculateTotal(selected.size, "12000.00"), "24000.00");
  dropUnavailable(selected, SEATS.map((seat) => ({ ...seat, is_available: false })));
  assert.equal(calculateTotal(selected.size, "12000.00"), "0.00");
});

test("takenSeatsMessage names one seat or several, and says nothing for none", () => {
  assert.match(takenSeatsMessage(["D5"]), /^Seat D5 was just taken by someone else and removed from your selection/);
  assert.match(takenSeatsMessage(["A4", "B5"]), /^Seats A4, B5 were just taken/);
  assert.equal(takenSeatsMessage([]), "");
  assert.equal(takenSeatsMessage(undefined), "");
});
