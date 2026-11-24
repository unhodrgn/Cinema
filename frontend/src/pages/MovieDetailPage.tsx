import { useResource } from "../hooks/useResource";
import { Poster } from "../features/movies/MovieCard";
import { ShowtimeSelector } from "../features/showtimes/ShowtimeSelector";
import { isIdText, formatDuration } from "../../js/format.js";
import type { Movie } from "../types/cinema";

export function MovieDetailPage() {
  const id = new URLSearchParams(location.search).get("id");
  const { data, error } = useResource<{ movie: Movie }>(
    isIdText(id) ? "/api/movies/" + id : null,
  );
  if (!data)
    return (
      <p role="status">
        {error ||
          (isIdText(id) ? "Loading movie…" : "This movie could not be found.")}
      </p>
    );
  const m = data.movie;
  return (
    <>
      <p>
        <a href="/movies.html">← All movies</a>
      </p>
      <article className="movie-detail">
        <Poster title={m.title} url={m.poster_url} size="lg" />
        <div>
          <h1>{m.title}</h1>
          <dl className="facts">
            <dt>Genre</dt>
            <dd>{m.genre || "Not given"}</dd>
            <dt>Running time</dt>
            <dd>{formatDuration(m.duration_minutes)}</dd>
            <dt>Rating</dt>
            <dd>{m.rating || "Not given"}</dd>
            <dt>Release date</dt>
            <dd>{m.release_date || "Not given"}</dd>
          </dl>
          <h2>Synopsis</h2>
          <p className="synopsis">{m.synopsis || "Not given"}</p>
        </div>
      </article>
      <div className="section-gap">
        <h2>Screenings</h2>
        <ShowtimeSelector movieId={m.movie_id} />
      </div>
    </>
  );
}
