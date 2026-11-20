// Registration page. Sends only the account ID and the password; the server decides the
// role (always CUSTOMER) and answers duplicate IDs and invalid input with messages.

import { getAuth, safeNext } from "../auth.js";
import { clearFormErrors, showFormError } from "../forms.js";
import { initNav } from "../nav.js";
import { setFieldError } from "../ui.js";

const form = document.getElementById("register-form");
const messageBox = document.getElementById("form-message");
const fields = {
  username: { input: document.getElementById("username"), error: document.getElementById("username-error") },
  password: { input: document.getElementById("password"), error: document.getElementById("password-error") },
};
const submit = document.getElementById("submit");

const destination = safeNext(new URLSearchParams(globalThis.location.search).get("next"));
const auth = getAuth();

initNav(document.getElementById("site-nav"));

if (destination !== "/") {
  document.getElementById("login-link").setAttribute(
    "href", `/login.html?next=${encodeURIComponent(destination)}`);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault(); // never let the browser submit credentials itself
  clearFormErrors(fields, messageBox);

  const username = fields.username.input.value;
  const password = fields.password.input.value;
  let valid = true;
  if (username.trim() === "") {
    setFieldError(fields.username.input, fields.username.error, "Account ID is required.");
    valid = false;
  }
  if (password === "") {
    setFieldError(fields.password.input, fields.password.error, "Password is required.");
    valid = false;
  }
  if (!valid) return;

  submit.disabled = true;
  try {
    await auth.register(username, password);
    const next = destination === "/" ? "" : `&next=${encodeURIComponent(destination)}`;
    globalThis.location.assign(`/login.html?registered=1${next}`);
  } catch (error) {
    fields.password.input.value = "";
    showFormError(error, fields, messageBox);
    submit.disabled = false;
  }
});
