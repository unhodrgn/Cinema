import { Fragment } from "react";
import type { AvailableSeat } from "../../types/cinema";
import { groupSeatsByRow, seatLabel } from "../../../js/seats.js";

export function SeatMap({
  seats,
  selection,
  toggle,
  disabled,
}: {
  seats: AvailableSeat[];
  selection: Set<number>;
  toggle: (id: number) => void;
  disabled: boolean;
}) {
  const rows: Map<string, AvailableSeat[]> = groupSeatsByRow(seats);
  return (
    <div className="card seat-map">
      <div className="screen-box">SCREEN</div>
      <div className="seat-grid">
        {[...rows].map(([letter, row]) => (
          <div className="seat-row" key={letter}>
            <span className="seat-row-label">{letter}</span>
            {row.map((s) => (
              <Fragment key={s.seat_id}>
                {s.seat_number === 6 && <span className="seat-aisle" />}
                <button
                  className={
                    "seat-btn" +
                    (!s.is_available
                      ? " occupied"
                      : selection.has(s.seat_id)
                        ? " selected"
                        : "")
                  }
                  aria-label={
                    "Seat " +
                    seatLabel(s) +
                    (s.is_available ? "" : " (Occupied)")
                  }
                  aria-pressed={selection.has(s.seat_id)}
                  disabled={disabled || !s.is_available}
                  onClick={() => toggle(s.seat_id)}
                >
                  {s.seat_number}
                </button>
              </Fragment>
            ))}
            <span className="seat-row-label">{letter}</span>
          </div>
        ))}
      </div>
      <div className="seat-legend">
        {["Available", "Selected", "Occupied"].map((label) => (
          <div key={label} className="legend-item">
            <span className={"legend-box " + label.toLowerCase()} />
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}
