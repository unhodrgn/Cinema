import assert from "node:assert/strict";
import { test } from "node:test";

import {
  calculateTotal,
  formatSelectedSeats,
  groupSeatsByRow,
  parseSelectedSeats,
  seatLabel,
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
