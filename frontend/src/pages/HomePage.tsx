import { useResource } from "../hooks/useResource";
import { MovieCard, Poster } from "../features/movies/MovieCard";
import { formatTime, formatDuration } from "../../js/format.js";
import { pickFeatured } from "../../js/home.js";
import type { Movie, Schedule, Showtime } from "../types/cinema";

export function MoviesPage() {
  const { data, error } = useResource<{ movies: Movie[] }>("/api/movies");
  return (
    <>
      <h1>Movies</h1>
      {error && <p role="alert">{error}</p>}
      {!data && !error && <p role="status">Loading movies…</p>}
      {data && !data.movies.length && <p>No movies are registered yet.</p>}
      <div className="grid">
        {data?.movies.map((movie) => (
          <MovieCard key={movie.movie_id} movie={movie} />
        ))}
      </div>
    </>
  );
}
function Times({
  screenings,
  titles = false,
}: {
  screenings: Showtime[];
  titles?: boolean;
}) {
  if (!screenings.length) return <p>No screenings today.</p>;
  return (
    <ul className={titles ? "chip-list chip-list-stacked" : "chip-list"}>
      {screenings.map((s) => (
        <li key={s.showtime_id}>
          {s.has_started ? (
            <span className="chip chip-closed">
              <span className="chip-time">{formatTime(s.starts_at)}</span>
              {titles && <span className="chip-title">{s.title}</span>}
            </span>
          ) : (
            <a
              className="chip"
              href={"/seats.html?screening_id=" + s.showtime_id}
            >
              <span className="chip-time">{formatTime(s.starts_at)}</span>
              {titles && <span className="chip-title">{s.title}</span>}
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}
export function HomePage() {
  const movies = useResource<{ movies: Movie[] }>("/api/movies");
  const schedule = useResource<Schedule>("/api/screenings");
  if (movies.error || schedule.error)
    return <p role="alert">{movies.error || schedule.error}</p>;
  if (!movies.data || !schedule.data)
    return <p role="status">Loading movies…</p>;
  const all = movies.data.movies;
  const times = schedule.data.screenings;
  const hero: Movie | null = pickFeatured(all, times);
  if (!hero) return <p>No movies are registered yet.</p>;
  const halls = [...new Set(times.map((s) => s.room_name))].sort();
  return (
    <>
      <h1 className="visually-hidden">Cinema Reservation System</h1>
      <section className="hero">
        <Poster title={hero.title} url={hero.poster_url} size="lg" />
        <div className="hero-body">
          <p className="eyebrow">Featured</p>
          <h2 className="hero-title">{hero.title}</h2>
          <p className="hero-facts">
            {[hero.genre, formatDuration(hero.duration_minutes)]
              .filter(Boolean)
              .join(" · ")}
            {hero.rating && (
              <span className="badge badge-rating">Rated {hero.rating}</span>
            )}
          </p>
          <p className="synopsis">{hero.synopsis}</p>
          <h3 className="hero-subtitle">Today’s showtimes</h3>
          <Times
            screenings={times.filter((s) => s.movie_id === hero.movie_id)}
          />
          <a className="button" href={"/movie.html?id=" + hero.movie_id}>
            Book tickets
          </a>
        </div>
      </section>
      <div className="section-head">
        <h2>Now Showing</h2>
        <a href="/movies.html">All movies</a>
      </div>
      <div className="poster-grid">
        {all.map((movie) => (
          <MovieCard key={movie.movie_id} movie={movie} tile />
        ))}
      </div>
      <div className="section-head">
        <h2>
          Today by hall <small>{schedule.data.date}</small>
        </h2>
        <a href="/screenings.html">Full schedule</a>
      </div>
      <div className="hall-grid">
        {halls.map((hall) => (
          <article className="hall card" key={hall}>
            <h3>{hall}</h3>
            <Times
              screenings={times.filter((s) => s.room_name === hall)}
              titles
            />
          </article>
        ))}
      </div>
    </>
  );
}
