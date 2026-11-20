// Small helpers shared by the form pages: show the server's validation messages next to the
// right fields, and any other error in the message box. All text goes in as text.

import { clear, describeError, setFieldError, showMessage } from "./ui.js";

/**
 * `fields` maps an API field name to `{ input, error }` (the input and the element that
 * shows its message). Returns nothing; clears everything first.
 */
export function clearFormErrors(fields, messageBox) {
  for (const { input, error } of Object.values(fields)) setFieldError(input, error, "");
  clear(messageBox);
}

/**
 * Show an ApiError. A `validation_error` with `fields` puts each message next to its input
 * (unknown field names are ignored); everything else is one message in the message box.
 */
export function showFormError(error, fields, messageBox) {
  let shown = false;
  if (error && error.fields && typeof error.fields === "object") {
    for (const [name, message] of Object.entries(error.fields)) {
      const target = Object.hasOwn(fields, name) ? fields[name] : null;
      if (target && typeof message === "string") {
        setFieldError(target.input, target.error, message);
        shown = true;
      }
    }
  }
  if (!shown) showMessage(messageBox, "error", describeError(error));
  return shown;
}
