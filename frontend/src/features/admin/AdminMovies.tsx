import { useState, type FormEvent } from "react";
import { getApi } from "../../../js/api.js";
import { useResource } from "../../hooks/useResource";
import { errorMessage } from "../../services/apiClient";
import type { Movie } from "../../types/cinema";

const fields = [
  ["title", "Title", "text", true],
  ["duration_minutes", "Running time (minutes)", "number", false],
  ["release_date", "Release date", "date", false],
  ["genre", "Genre", "text", false],
  ["rating", "Rating", "text", false],
  ["poster_url", "Poster path", "text", true],
  ["synopsis", "Synopsis", "textarea", true],
] as const;
export function AdminMovies() {
  const { data, error, reload } = useResource<{ movies: Movie[] }>(
    "/api/admin/movies",
  );
  const [editing, setEditing] = useState<Movie>();
  const [version, setVersion] = useState(0);
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [removal, setRemoval] = useState<{ text: string; failed: boolean }>();
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const body = Object.fromEntries(
      fields.map(([name]) => [
        name,
        name === "duration_minutes"
          ? Number(values.get(name))
          : String(values.get(name)).trim() || null,
      ]),
    );
    setBusy(true);
    setErrors({});
    setFailed(false);
    try {
      if (editing)
        await getApi().put("/api/admin/movies/" + editing.movie_id, body);
      else await getApi().post("/api/admin/movies", body);
      setMessage("Movie saved.");
      setFailed(false);
      setEditing(undefined);
      setVersion((v) => v + 1);
      reload();
    } catch (e) {
      setMessage(errorMessage(e));
      setFailed(true);
      setErrors((e as { fields?: Record<string, string> }).fields || {});
    } finally {
      setBusy(false);
    }
  }

  async function deleteMovie(movie: Movie) {
    if (
      busy ||
      !window.confirm(
        `Delete "${movie.title}"? Any upcoming screenings without bookings will also be removed.`,
      )
    ) {
      return;
    }
    setBusy(true);
    setRemoval(undefined);
    try {
      await getApi().request("DELETE", "/api/admin/movies/" + movie.movie_id);
      if (editing?.movie_id === movie.movie_id) {
        setEditing(undefined);
        setErrors({});
      }
      setMessage("");
      setRemoval({ text: `"${movie.title}" was deleted.`, failed: false });
      reload();
    } catch (e) {
      setRemoval({ text: errorMessage(e), failed: true });
    } finally {
      setBusy(false);
    }
  }

  const statusText = error || message;
  const statusFailed = Boolean(error) || failed;
  return (
    <>
      <h1>Manage Movies</h1>
      {statusText && (
        <p
          className={
            "message " + (statusFailed ? "message-error" : "message-success")
          }
          role={statusFailed ? "alert" : "status"}
        >
          {statusText}
        </p>
      )}
      <section className="card">
        <h2>{editing ? "Edit Movie #" + editing.movie_id : "Add New Movie"}</h2>
        <form
          key={(editing?.movie_id || 0) + "-" + version}
          className="form"
          onSubmit={save}
        >
          <div className="form-grid">
            {fields.map(([name, label, type, full]) => (
              <div
                className={full ? "field field-full" : "field"}
                key={name}
              >
                <label htmlFor={name}>{label}</label>
                {type === "textarea" ? (
                  <textarea
                    id={name}
                    name={name}
                    rows={3}
                    defaultValue={editing?.[name] || ""}
                    aria-invalid={errors[name] ? true : undefined}
                    aria-describedby={errors[name] ? name + "-error" : undefined}
                  />
                ) : (
                  <input
                    id={name}
                    name={name}
                    type={type}
                    defaultValue={editing?.[name] ?? ""}
                    required={name === "title" || type === "number"}
                    aria-invalid={errors[name] ? true : undefined}
                    aria-describedby={errors[name] ? name + "-error" : undefined}
                  />
                )}
                {errors[name] && (
                  <p className="field-error" id={name + "-error"}>
                    {errors[name]}
                  </p>
                )}
              </div>
            ))}
          </div>
          <div className="form-actions">
            <button className="button" disabled={busy}>
              Save Movie
            </button>
            {editing && (
              <button
                type="button"
                className="button button-secondary"
                disabled={busy}
                onClick={() => {
                  setEditing(undefined);
                  setErrors({});
                  setMessage("");
                  setFailed(false);
                }}
              >
                Cancel Edit
              </button>
            )}
          </div>
        </form>
      </section>
      <section className="section-gap">
        <h2>All Movies</h2>
        {removal && (
          <p
            className={
              "message " + (removal.failed ? "message-error" : "message-success")
            }
            role={removal.failed ? "alert" : "status"}
          >
            {removal.text}
          </p>
        )}
        <div className="card card-flush">
          {data && data.movies.length === 0 ? (
            <p className="muted empty-note">No movies registered yet.</p>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    {[
                      "ID",
                      "Title",
                      "Genre",
                      "Running time",
                      "Rating",
                      "Release date",
                      "Actions",
                    ].map((label) => (
                      <th key={label}>{label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data?.movies.map((m) => (
                    <tr key={m.movie_id}>
                      <td>{m.movie_id}</td>
                      <td className="cell-strong">{m.title}</td>
                      <td>{m.genre || "-"}</td>
                      <td>{m.duration_minutes} min</td>
                      <td>{m.rating || "-"}</td>
                      <td>{m.release_date || "-"}</td>
                      <td className="cell-actions">
                        <div className="table-actions">
                          <button
                            className="button button-small button-secondary"
                            disabled={busy}
                            onClick={() => {
                              setEditing(m);
                              setErrors({});
                              setMessage("");
                              setFailed(false);
                              window.scrollTo(0, 0);
                            }}
                          >
                            Edit
                          </button>
                          <button
                            className="button button-small button-danger"
                            disabled={busy}
                            type="button"
                            onClick={() => deleteMovie(m)}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </>
  );
}
