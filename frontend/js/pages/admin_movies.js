// Admin Movie Management (T7, A-01).
// Allows listing, adding, and editing movies.

import { getApi } from "../api.js";
import { dataTable, requireAdmin } from "../admin.js";
import { formatDuration } from "../format.js";
import { initNav } from "../nav.js";
import { clear, el, setFieldError, showMessage } from "../ui.js";

const FIELDS = ["title", "duration_minutes", "genre", "rating", "release_date", "poster_url", "synopsis"];

async function main() {
  await initNav(document.getElementById("site-nav"));

  const messageBox = document.getElementById("message");
  const formSection = document.getElementById("form-section");
  const user = await requireAdmin({
    page: "/admin-movies.html",
    messageBox,
    hideNode: formSection,
    what: "manage movies",
  });
  if (!user) return;

  const form = document.getElementById("movie-form");
  const formTitle = document.getElementById("form-title");
  const idInput = document.getElementById("movie-id");
  const titleInput = document.getElementById("movie-title");
  const durationInput = document.getElementById("movie-duration");
  const genreInput = document.getElementById("movie-genre");
  const ratingInput = document.getElementById("movie-rating");
  const releaseInput = document.getElementById("movie-release");
  const posterInput = document.getElementById("movie-poster");
  const synopsisInput = document.getElementById("movie-synopsis");
  const cancelBtn = document.getElementById("cancel-btn");
  const container = document.getElementById("movies-container");

  function clearFormErrors() {
    for (const name of FIELDS) {
      const errorNode = document.getElementById(`error-${name}`);
      const input = form.elements[name];
      if (errorNode && input) setFieldError(input, errorNode, "");
    }
  }

  function resetForm() {
    clearFormErrors();
    form.reset();
    idInput.value = "";
    formTitle.textContent = "Add New Movie";
    cancelBtn.hidden = true;
  }

  function startEdit(movie) {
    clearFormErrors();
    clear(messageBox);
    idInput.value = String(movie.movie_id);
    titleInput.value = movie.title || "";
    durationInput.value = movie.duration_minutes || "";
    genreInput.value = movie.genre || "";
    ratingInput.value = movie.rating || "";
    releaseInput.value = movie.release_date || "";
    posterInput.value = movie.poster_url || "";
    synopsisInput.value = movie.synopsis || "";
    formTitle.textContent = `Edit Movie #${movie.movie_id}: ${movie.title}`;
    cancelBtn.hidden = false;
    form.scrollIntoView({ behavior: "smooth" });
  }

  cancelBtn.addEventListener("click", () => {
    resetForm();
    clear(messageBox);
  });

  async function loadMovies() {
    clear(container);
    try {
      const data = await getApi().get("/api/admin/movies");
      const movies = data.movies || [];

      if (movies.length === 0) {
        container.append(el("p", { className: "muted empty-note" }, "No movies registered yet."));
        return;
      }

      container.append(
        dataTable(
          [
            { header: "ID", cell: (m) => String(m.movie_id) },
            { header: "Title", className: "cell-strong", cell: (m) => m.title },
            { header: "Duration", cell: (m) => formatDuration(m.duration_minutes) },
            { header: "Genre", cell: (m) => m.genre || "-" },
            { header: "Rating", cell: (m) => m.rating || "-" },
            { header: "Release Date", cell: (m) => m.release_date || "-" },
            { header: "Poster", cell: (m) => m.poster_url || "-" },
            {
              header: "Actions",
              className: "cell-actions",
              cell: (m) =>
                el("button", {
                  className: "button button-secondary",
                  attrs: { type: "button" },
                  text: "Edit",
                  on: { click: () => startEdit(m) },
                }),
            },
          ],
          movies,
        ),
      );
    } catch (err) {
      showMessage(messageBox, "error", err.message || "Failed to load movies.");
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFormErrors();
    clear(messageBox);

    const isEdit = Boolean(idInput.value);
    const movieId = idInput.value;

    const payload = {
      title: titleInput.value.trim(),
      duration_minutes: durationInput.value ? Number.parseInt(durationInput.value, 10) : null,
      genre: genreInput.value.trim() || null,
      rating: ratingInput.value.trim() || null,
      release_date: releaseInput.value.trim() || null,
      poster_url: posterInput.value.trim() || null,
      synopsis: synopsisInput.value.trim() || null,
    };

    try {
      const api = getApi();
      if (isEdit) {
        await api.put(`/api/admin/movies/${encodeURIComponent(movieId)}`, payload);
        showMessage(messageBox, "success", `Movie #${movieId} updated successfully.`);
      } else {
        const res = await api.post("/api/admin/movies", payload);
        showMessage(messageBox, "success", `Movie "${res.movie.title}" created successfully.`);
      }
      resetForm();
      await loadMovies();
    } catch (err) {
      if (err.fields) {
        for (const [name, message] of Object.entries(err.fields)) {
          const errorNode = document.getElementById(`error-${name}`);
          const input = form.elements[name];
          if (errorNode && input) setFieldError(input, errorNode, message);
        }
      }
      showMessage(messageBox, "error", err.message || "Failed to save movie.");
    }
  });

  await loadMovies();
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", main);
}
