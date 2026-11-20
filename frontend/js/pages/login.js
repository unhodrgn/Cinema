// Login page. Sends the account ID and password to the API; on success the token is kept for
// this tab (sessionStorage) and the browser goes to `?next=` if it is a known page.

import { getAuth, safeNext } from "../auth.js";
import { clearFormErrors, showFormError } from "../forms.js";
import { initNav } from "../nav.js";
import { setFieldError, showMessage } from "../ui.js";

const form = document.getElementById("login-form");
const messageBox = document.getElementById("form-message");
const fields = {
  username: { input: document.getElementById("username"), error: document.getElementById("username-error") },
  password: { input: document.getElementById("password"), error: document.getElementById("password-error") },
};
const submit = document.getElementById("submit");

const params = new URLSearchParams(globalThis.location.search);
const destination = safeNext(params.get("next"));
const auth = getAuth();

initNav(document.getElementById("site-nav"));

// Keep the destination when moving to the registration page.
if (destination !== "/") {
  document.getElementById("register-link").setAttribute(
    "href", `/register.html?next=${encodeURIComponent(destination)}`);
}
if (params.get("registered") === "1") {
  showMessage(messageBox, "success", "Your account was created. Please log in.");
}

// Already logged in (for example the user pressed "back")? Go straight on.
auth.currentUser().then((user) => {
  if (user) globalThis.location.assign(destination);
}).catch(() => { /* API unreachable: the form will explain when submitted */ });

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
    await auth.login(username, password);
    globalThis.location.assign(destination);
  } catch (error) {
    fields.password.input.value = ""; // never keep a rejected password in the form
    showFormError(error, fields, messageBox);
    submit.disabled = false;
  }
});
