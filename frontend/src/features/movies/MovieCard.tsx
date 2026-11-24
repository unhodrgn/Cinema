import { useState } from "react";
import { fallbackColour, posterPath } from "../../../js/poster.js";
import { movieFacts } from "../../../js/catalog.js";
import type { Movie } from "../../types/cinema";

export function Poster({
  title,
  url,
  size = "md",
}: {
  title: string;
  url: string | null;
  size?: string;
}) {
  const [failed, setFailed] = useState<string>();
  const src = posterPath(url);
  return (
    <div className={`poster poster-${size} poster-c${fallbackColour(title)}`}>
      <span
        className="poster-fallback"
        aria-hidden={src && src !== failed ? true : undefined}
      >
        {title}
      </span>
      {src && src !== failed && (
        <img
          className="poster-img"
          src={src}
          alt={title}
          loading="lazy"
          onError={() => setFailed(src)}
        />
      )}
    </div>
  );
}
export function MovieCard({
  movie,
  tile = false,
}: {
  movie: Movie;
  tile?: boolean;
}) {
  const href = "/movie.html?id=" + movie.movie_id;
  const Title = tile ? "h3" : "h2";
  return (
    <article className={tile ? "movie-tile" : "card movie-card"}>
      <a className="poster-link" href={href} aria-hidden="true" tabIndex={-1}>
        <Poster title={movie.title} url={movie.poster_url} />
      </a>
      <div className="movie-card-body">
        <Title className="movie-title">
          <a href={href}>{movie.title}</a>
        </Title>
        <p className="muted">{movieFacts(movie)}</p>
        {!tile && <p className="synopsis">{movie.synopsis}</p>}
      </div>
    </article>
  );
}
