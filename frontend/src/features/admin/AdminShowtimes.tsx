import { useEffect, useState, type FormEvent } from "react";
import { getApi } from "../../../js/api.js";
import { screeningEditLock, toInputDateTime } from "../../../js/admin.js";
import { formatDateTimeRange, formatMoney } from "../../../js/format.js";
import { errorMessage } from "../../services/apiClient";
import { useResource } from "../../hooks/useResource";
import type { Movie, Showtime } from "../../types/cinema";

type Room = { room_id: number; room_name: string };

export function AdminShowtimes() {
  const [filter, setFilter] = useState("");
  const movies = useResource<{ movies: Movie[] }>("/api/admin/movies");
  const { data, error, reload } = useResource<{
    screenings: Showtime[];
    rooms: Room[];
  }>("/api/admin/screenings?movie_id=" + filter);
  const [rooms, setRooms] = useState<Room[]>([]);
  useEffect(() => {
    if (data) setRooms(data.rooms);
  }, [data]);
  const [editing, setEditing] = useState<Showtime>();
  const [version, setVersion] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [removal, setRemoval] = useState<{ text: string; failed: boolean }>();
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setErrors({});
    const form = new FormData(event.currentTarget);
    const body = {
      movie_id: Number(form.get("movie_id")),
      room_id: Number(form.get("room_id")),
      starts_at: form.get("starts_at"),
      ends_at: form.get("ends_at") || null,
      ticket_price: form.get("ticket_price"),
    };
    try {
      if (editing)
        await getApi().put(
          "/api/admin/screenings/" + editing.showtime_id,
          body,
        );
      else await getApi().post("/api/admin/screenings", body);
      setMessage("Screening saved.");
      setEditing(undefined);
      setVersion((v) => v + 1);
      reload();
    } catch (e) {
      setMessage(errorMessage(e));
      setErrors((e as { fields?: Record<string, string> }).fields || {});
    } finally {
      setBusy(false);
    }
  }

  async function deleteScreening(screening: Showtime) {
    if (busy || screeningEditLock(screening).disabled) return;
    const time = formatDateTimeRange(screening.starts_at, screening.ends_at);
    if (
      !window.confirm(
        `Delete screening #${screening.showtime_id} for "${screening.title}" in ${screening.room_name}?\n${time}`,
      )
    ) {
      return;
    }
    setBusy(true);
    setRemoval(undefined);
    try {
      await getApi().request(
        "DELETE",
        "/api/admin/screenings/" + screening.showtime_id,
      );
      if (editing?.showtime_id === screening.showtime_id) {
        setEditing(undefined);
        setErrors({});
      }
      setMessage("");
      setRemoval({
        text: `Screening #${screening.showtime_id} was deleted.`,
        failed: false,
      });
      reload();
    } catch (e) {
      setRemoval({ text: errorMessage(e), failed: true });
      reload();
    } finally {
      setBusy(false);
    }
  }

  const options = movies.data?.movies.map((m) => (
    <option key={m.movie_id} value={m.movie_id}>
      {m.title}
    </option>
  ));
  return (
    <>
      <h1>Manage Screenings</h1>
      <p role="status">{error || movies.error || message}</p>
      <section className="card">
        <h2>
          {editing
            ? "Edit Screening #" + editing.showtime_id
            : "Add New Screening"}
        </h2>
        <form
          key={(editing?.showtime_id || 0) + "-" + version}
          className="form"
          onSubmit={save}
        >
          <div className="field">
            <label htmlFor="screening-movie">Movie</label>
            <select
              id="screening-movie"
              name="movie_id"
              required
              defaultValue={editing?.movie_id || ""}
            >
              <option value="">Select a movie</option>
              {options}
            </select>
          </div>
          <div className="field">
            <label htmlFor="screening-room">Room</label>
            <select
              id="screening-room"
              name="room_id"
              required
              defaultValue={editing?.room_id || ""}
            >
              <option value="">Select a room</option>
              {rooms.map((r) => (
                <option key={r.room_id} value={r.room_id}>
                  {r.room_name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="screening-start">Start time</label>
            <input
              id="screening-start"
              type="datetime-local"
              name="starts_at"
              required
              defaultValue={toInputDateTime(editing?.starts_at)}
            />
          </div>
          <div className="field">
            <label htmlFor="screening-end">End time</label>
            <input
              id="screening-end"
              type="datetime-local"
              name="ends_at"
              defaultValue={toInputDateTime(editing?.ends_at)}
            />
          </div>
          <div className="field">
            <label htmlFor="screening-price">Ticket price</label>
            <input
              id="screening-price"
              name="ticket_price"
              type="number"
              min="0"
              step="0.01"
              required
              defaultValue={editing?.ticket_price}
            />
          </div>
          {Object.entries(errors).map(([field, text]) => (
            <span key={field} className="field-error">
              {text}
            </span>
          ))}
          <div className="form-actions">
            <button
              className="button"
              disabled={busy || !rooms.length || !movies.data}
            >
              Save Screening
            </button>{" "}
            {editing && (
              <button
                type="button"
                className="button button-secondary"
                disabled={busy}
                onClick={() => {
                  setEditing(undefined);
                  setErrors({});
                  setMessage("");
                }}
              >
                Cancel Edit
              </button>
            )}
          </div>
        </form>
      </section>
      <h2 className="section-gap">Screenings</h2>
      <div className="toolbar">
        <label htmlFor="screening-movie-filter">Filter by movie</label>
        <select
          id="screening-movie-filter"
          disabled={busy}
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="">All Movies</option>
          {options}
        </select>
      </div>
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
      {data && data.screenings.length === 0 && <p>No screenings found.</p>}
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              {[
                "ID",
                "Movie",
                "Room",
                "Screening",
                "Price",
                "Status",
                "Actions",
              ].map((label) => (
                <th key={label}>{label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data?.screenings.map((s) => {
              const lock = screeningEditLock(s);
              return (
                <tr key={s.showtime_id}>
                  <td>{s.showtime_id}</td>
                  <td>{s.title}</td>
                  <td>{s.room_name}</td>
                  <td>{formatDateTimeRange(s.starts_at, s.ends_at)}</td>
                  <td>{formatMoney(s.ticket_price)}</td>
                  <td>
                    {s.has_bookings
                      ? "Has bookings (locked)"
                      : s.has_started
                        ? "Started"
                        : "Editable"}
                  </td>
                  <td className="cell-actions">
                    <button
                      className="button button-small button-secondary"
                      disabled={busy || lock.disabled}
                      title={lock.title || undefined}
                      onClick={() => {
                        setEditing(s);
                        setErrors({});
                        setMessage("");
                        window.scrollTo(0, 0);
                      }}
                    >
                      Edit
                    </button>{" "}
                    <button
                      className="button button-small button-danger"
                      type="button"
                      disabled={busy || lock.disabled}
                      title={
                        lock.disabled
                          ? "Only upcoming screenings without booking history can be deleted."
                          : undefined
                      }
                      onClick={() => deleteScreening(s)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
