import { useState } from "react";
import { parseSelectedSeats } from "../../js/seats.js";
import type { AvailableSeat } from "../types/cinema";

export function useBookingStore() {
  const [selection, setSelection] = useState<Set<number>>(
    () =>
      new Set(
        parseSelectedSeats(
          new URLSearchParams(location.search).get("selected"),
        ),
      ),
  );
  function toggle(id: number) {
    setSelection((previous) => {
      const next = new Set(previous);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  function reconcile(seats: AvailableSeat[]) {
    const free = new Set(
      seats.filter((s) => s.is_available).map((s) => s.seat_id),
    );
    setSelection(
      (previous) => new Set([...previous].filter((id) => free.has(id))),
    );
  }
  return { selection, toggle, reconcile };
}
