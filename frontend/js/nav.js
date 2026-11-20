// The site navigation shown at the top of every page. It asks the API who is logged in
// (through auth.js) and builds the links with text nodes only: the account ID comes from
// the API and is never parsed as HTML.

import { getAuth } from "./auth.js";
import { clear, el } from "./ui.js";

function link(href, text) {
  return el("a", { className: "nav-link", attrs: { href }, text });
}

export async function initNav(container) {
  const auth = getAuth();
  let user = null;
  try {
    user = await auth.currentUser();
  } catch {
    user = null; // the API cannot be reached: show the logged-out links, the page explains the rest
  }

  clear(container);
  container.append(link("/", "Home"), link("/movies.html", "Movies"), link("/screenings.html", "Schedule"));
  if (user) {
    container.append(
      el("span", { className: "nav-user", text: `${user.username} (${user.role})` }),
      el("button", {
        className: "nav-button",
        attrs: { type: "button" },
        text: "Log out",
        on: {
          click: async () => {
            await auth.logout();
            globalThis.location.assign("/");
          },
        },
      }),
    );
  } else {
    container.append(link("/login.html", "Log in"), link("/register.html", "Register"));
  }
}
