import { useState } from "react";
import { useResource } from "../../hooks/useResource";
import {
  formatTimeRange,
  formatMoney,
  isDateText,
} from "../../../js/format.js";
import { Poster } from "../movies/MovieCard";
import type { Schedule } from "../../types/cinema";

export function ShowtimeSelector({ movieId }: { movieId?: number }) {
  const requested = new URLSearchParams(location.search).get("date");
  const [day, setDay] = useState(isDateText(requested) ? requested || "" : "");
  const query = new URLSearchParams();
  if (day) query.set("date", day);
  if (movieId) query.set("movie_id", String(movieId));
  const { data, error } = useResource<Schedule>("/api/screenings?" + query);
  return (
    <section>
      <div className="toolbar">
        <label htmlFor="date">Screening date</label>
        <input
          id="date"
          type="date"
          value={day || data?.date || ""}
          onChange={(e) => setDay(e.target.value)}
        />
      </div>
      {error && (
        <p className="message message-error" role="alert">
          {error}
        </p>
      )}
      {!data && !error && <p role="status">Loading screenings…</p>}
      {data && !data.screenings.length && (
        <p>There are no screenings on this day.</p>
      )}
      {data && data.screenings.length > 0 && (
        <ul className="screening-list card">
          {data.screenings.map((s) => (
            <li
              key={s.showtime_id}
              className={
                movieId ? "screening" : "screening screening-with-poster"
              }
            >
              {!movieId && (
                <Poster title={s.title} url={s.poster_url} size="sm" />
              )}
              <strong className="time">
                {formatTimeRange(s.starts_at, s.ends_at)}
              </strong>
              {!movieId && (
                <a
                  className="screening-movie"
                  href={"/movie.html?id=" + s.movie_id}
                >
                  {s.title}
                </a>
              )}
              <span>{s.room_name}</span>
              <span className="muted">
                Price per seat: {formatMoney(s.ticket_price)}
              </span>
              {s.has_started ? (
                <span className="badge badge-neutral">Already started</span>
              ) : (
                <a
                  className="button button-small"
                  href={"/seats.html?screening_id=" + s.showtime_id}
                >
                  Select Seats
                </a>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
