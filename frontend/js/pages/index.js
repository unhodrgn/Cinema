// Home page: shows whether the API (and, through it, the database) is reachable.
// It demonstrates the three separated layers: this page comes from the frontend server,
// /health comes from the Flask API, and /health/db reports on PostgreSQL via the API.

import { getApi } from "../api.js";
import { initNav } from "../nav.js";
import { clear, describeError, el, setText, showMessage } from "../ui.js";

function setBadge(service, kind, text) {
  const item = document.querySelector(`[data-service="${service}"]`);
  const old = item.querySelector(".badge");
  old.replaceWith(el("span", { className: `badge badge-${kind}`, text }));
}

async function check(api, path, okValue) {
  try {
    const body = await api.get(path, { auth: false });
    return body && Object.values(body).includes(okValue) ? { ok: true } : { ok: false };
  } catch (error) {
    return { ok: false, error };
  }
}

async function main() {
  initNav(document.getElementById("site-nav"));
  const message = document.getElementById("status-message");
  let api;
  try {
    api = getApi();
  } catch {
    setBadge("api", "error", "not configured");
    setBadge("database", "error", "unknown");
    showMessage(message, "error", "The API address is not configured (API_BASE_URL).");
    return;
  }
  setText(document.getElementById("api-address"), api.baseUrl);

  const apiResult = await check(api, "/health", "ok");
  setBadge("api", apiResult.ok ? "ok" : "error", apiResult.ok ? "reachable" : "unreachable");
  if (!apiResult.ok) {
    setBadge("database", "error", "unknown");
    showMessage(message, "error", describeError(apiResult.error));
    return;
  }

  const dbResult = await check(api, "/health/db", "ok");
  setBadge("database", dbResult.ok ? "ok" : "error", dbResult.ok ? "ok" : "unavailable");
  if (dbResult.ok) {
    clear(message);
  } else {
    showMessage(message, "error", "The API is running but cannot reach the database.");
  }
}

main();
