// Tests for js/ui.js with a minimal fake DOM. Run: node --test tests/ui.test.js (from frontend/)

import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { clear, describeError, el, safeHref, setText, showMessage } from "../js/ui.js";
import { ApiError } from "../js/api.js";

class FakeNode {
  constructor(tag) {
    this.tag = tag;
    this.attributes = {};
    this.children = [];
    this.listeners = {};
    this.className = "";
    this._text = "";
  }
  // Parsing HTML is exactly what must never happen:
  set innerHTML(value) { throw new Error("innerHTML must not be used"); }
  set outerHTML(value) { throw new Error("outerHTML must not be used"); }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(""); }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener(event, handler) { this.listeners[event] = handler; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren() { this.children = []; this._text = ""; }
}

class FakeText {
  constructor(text) { this.text = text; }
  get textContent() { return this.text; }
}

const fakeDocument = {
  createElement: (tag) => new FakeNode(tag),
  createTextNode: (text) => new FakeText(text),
};

let original;
beforeEach(() => { original = globalThis.document; globalThis.document = fakeDocument; });
afterEach(() => { globalThis.document = original; });

test("safeHref allows only same-site links", () => {
  for (const ok of ["/movies", "/movies/3?x=1", "#top", "?page=2"]) assert.equal(safeHref(ok), ok);
  for (const bad of ["javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,x", "//evil.example",
    "http://evil.example", "https://evil.example", "movies", "", " ", "/a\\b", "/\u0000x", null, undefined, 5]) {
    assert.equal(safeHref(bad), null, String(bad));
  }
});

test("el puts untrusted text in as text, never as markup", () => {
  const hostile = '<img src=x onerror=alert(1)><script>alert(2)</script>';

  const node = el("p", { text: hostile }, hostile);

  assert.equal(node._text, hostile);
  assert.ok(node.children[0] instanceof FakeText);
  assert.equal(node.children[0].text, hostile);
});

test("el refuses unsafe tags and attributes", () => {
  for (const tag of ["script", "iframe", "object", "embed", "style", "link", "meta", "base", "SCRIPT", "a b", "img onerror"]) {
    assert.throws(() => el(tag), undefined, tag);
  }
  assert.throws(() => el("div", { attrs: { onclick: "alert(1)" } }));
  assert.throws(() => el("div", { attrs: { onmouseover: "x" } }));
  assert.throws(() => el("div", { attrs: { style: "x" } }));
  assert.throws(() => el("div", { attrs: { srcdoc: "x" } }));
  assert.throws(() => el("a", { attrs: { href: "javascript:alert(1)" } }));
  assert.throws(() => el("a", { attrs: { href: "https://evil.example" } }));
  assert.throws(() => el("button", { on: { click: "alert(1)" } }));
});

test("el builds allowed elements with attributes, handlers and children", () => {
  const handler = () => {};
  const node = el("a", { className: "btn", attrs: { href: "/movies", "data-id": 3, "aria-label": "Movies", disabled: false, hidden: true }, on: { click: handler } },
    "Go", el("span", { text: "!" }), null, false);

  assert.equal(node.tag, "a");
  assert.equal(node.className, "btn");
  assert.deepEqual(node.attributes, { href: "/movies", "data-id": "3", "aria-label": "Movies", hidden: "" });
  assert.equal(node.listeners.click, handler);
  assert.equal(node.textContent, "Go!");
});

test("clear, setText and showMessage use text only", () => {
  const box = el("div");
  box.append(el("p", { text: "old" }));

  showMessage(box, "error", "<b>nope</b>");

  assert.equal(box.children.length, 1);
  assert.equal(box.children[0].attributes.role, "alert");
  assert.equal(box.children[0].className, "message message-error");
  assert.equal(box.textContent, "<b>nope</b>");
  showMessage(box, "weird-kind", "hi");
  assert.equal(box.children[0].className, "message message-info");
  assert.equal(box.children[0].attributes.role, "status");
  assert.equal(setText(box, "<i>x</i>")._text, "<i>x</i>");
  assert.equal(clear(box).children.length, 0);
});

test("describeError shows the server's fixed message or a safe fallback", () => {
  assert.equal(describeError(new ApiError({ status: 409, code: "seat_unavailable", message: "Choose again." })), "Choose again.");
  assert.equal(describeError(new ApiError({ status: 0, code: "network_error", message: "Cannot reach." })), "Cannot reach.");
  assert.equal(describeError(new Error("TypeError: secret detail")), "Something went wrong. Please try again.");
  assert.equal(describeError(null), "Something went wrong. Please try again.");
  assert.equal(describeError(undefined), "Something went wrong. Please try again.");
});

test("setFieldError shows and clears a field message as text", async () => {
  const { setFieldError } = await import("../js/ui.js");
  const attributes = {};
  const input = { setAttribute: (n, v) => { attributes[n] = v; }, removeAttribute: (n) => { delete attributes[n]; } };
  const error = { textContent: "", hidden: true };

  setFieldError(input, error, "<i>Required.</i>");
  assert.equal(error.textContent, "<i>Required.</i>");
  assert.equal(error.hidden, false);
  assert.equal(attributes["aria-invalid"], "true");

  setFieldError(input, error, "");
  assert.equal(error.textContent, "");
  assert.equal(error.hidden, true);
  assert.equal(attributes["aria-invalid"], undefined);
});
