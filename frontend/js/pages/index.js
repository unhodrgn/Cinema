// Home page: a short welcome. If the API cannot be reached, say so (the other pages would fail too).

import { getApi } from "../api.js";
import { initNav } from "../nav.js";
import { describeError, showMessage } from "../ui.js";

async function main() {
  initNav(document.getElementById("site-nav"));
  const message = document.getElementById("status-message");
  try {
    await getApi().get("/health", { auth: false });
  } catch (error) {
    showMessage(message, "error", describeError(error));
  }
}

main();
