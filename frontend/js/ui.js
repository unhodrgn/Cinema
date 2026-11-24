// Safe DOM helpers. API data is untrusted text: it must only ever reach the page through
// these helpers, which use textContent / text nodes and never parse HTML.
// There is deliberately no innerHTML, outerHTML, insertAdjacentHTML or document.write
// anywhere in the frontend (a test enforces it).

const FORBIDDEN_TAGS = new Set(["script", "iframe", "object", "embed", "style", "link", "meta", "base"]);
const TAG_NAME = /^[a-z][a-z0-9-]*$/;
const ATTRIBUTE_NAME =
  /^(aria-[a-z-]+|data-[a-z0-9-]+|class|id|href|type|name|value|for|role|title|placeholder|disabled|hidden|min|max|step|required|autocomplete|colspan|scope|selected|checked|maxlength|minlength|pattern|inputmode|tabindex|lang|src|alt|loading|decoding)$/;

/** `value` if it is a same-site link (`/path`, `#anchor`, `?query`), else null. */
export function safeHref(value) {
  if (typeof value !== "string") return null;
  const text = value.trim();
  if (/[\u0000-\u001f\\]/.test(text)) return null;
  if (text.startsWith("//")) return null;
  return /^(\/|#|\?)/.test(text) ? text : null;
}

/**
 * Create an element. `props`: `className`, `text`, `attrs` ({name: value}), `on` ({event: fn}).
 * `children`: nodes or strings (strings become text nodes). Unsafe tags and attributes
 * (anything starting with "on", unknown names, non-local hrefs) are refused.
 */
export function el(tag, props = {}, ...children) {
  if (!TAG_NAME.test(tag) || FORBIDDEN_TAGS.has(tag)) throw new Error(`tag not allowed: ${tag}`);
  const doc = globalThis.document;
  const node = doc.createElement(tag);
  if (props.className) node.className = props.className;
  if (props.text !== undefined) node.textContent = String(props.text);
  for (const [name, raw] of Object.entries(props.attrs ?? {})) {
    if (!ATTRIBUTE_NAME.test(name)) throw new Error(`attribute not allowed: ${name}`);
    if (raw === false || raw === null || raw === undefined) continue;
    if (name === "href" || name === "src") {
      const link = safeHref(raw); // images are same-site too (the CSP agrees: img-src 'self')
      if (link === null) throw new Error(`${name} must be a same-site link`);
      node.setAttribute(name, link);
    } else {
      node.setAttribute(name, raw === true ? "" : String(raw));
    }
  }
  for (const [event, handler] of Object.entries(props.on ?? {})) {
    if (typeof handler !== "function") throw new Error("event handler must be a function");
    node.addEventListener(event, handler);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(typeof child === "string" || typeof child === "number"
      ? doc.createTextNode(String(child))
      : child);
  }
  return node;
}

/** Remove every child of `node`. */
export function clear(node) {
  node.replaceChildren();
  return node;
}

/** Replace the content of `node` with `text` (as text, never as HTML). */
export function setText(node, text) {
  node.textContent = String(text);
  return node;
}

/**
 * Show (or clear, when `message` is empty) the validation message of one form field.
 * `errorNode` is the element next to the input that holds the text.
 */
export function setFieldError(input, errorNode, message) {
  if (message) {
    errorNode.textContent = String(message);
    errorNode.hidden = false;
    input.setAttribute("aria-invalid", "true");
  } else {
    errorNode.textContent = "";
    errorNode.hidden = true;
    input.removeAttribute("aria-invalid");
  }
}

/** A user-facing sentence for an error: the server's fixed message, or a safe fallback. */
export function describeError(error) {
  if (error && typeof error.message === "string" && error.message) {
    if (error.code === "network_error" || error.code === "timeout" || error.status) {
      return error.message;
    }
  }
  return "Something went wrong. Please try again.";
}

/** Show a message in `container` (replacing earlier ones). `kind`: "info" | "success" | "error". */
export function showMessage(container, kind, text) {
  const allowed = ["info", "success", "error"];
  const safeKind = allowed.includes(kind) ? kind : "info";
  clear(container);
  container.append(
    el("p", { className: `message message-${safeKind}`, attrs: { role: safeKind === "error" ? "alert" : "status" }, text }),
  );
}
