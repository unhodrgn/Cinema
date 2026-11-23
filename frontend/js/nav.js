// The site navigation shown at the top of every page. It asks the API who is logged in
// (through auth.js) and builds the links with text nodes only: the account ID comes from
// the API and is never parsed as HTML.

import { getAuth, pageUser } from "./auth.js";
import { clear, el } from "./ui.js";

function link(href, text) {
  return el("a", { className: "nav-link", attrs: { href }, text });
}

/**
 * Build the navigation. Three states, never mixed up:
 *  - logged in -> links for the role, the account and Log out;
 *  - logged out (no token, or the API said 401) -> Log in and Register;
 *  - unknown (the API cannot be reached, or 5xx, with a token in the browser) -> only the public
 *    links and a neutral "Account unavailable". A person who is logged in must not be offered
 *    "Log in / Register" just because the server is down; the page itself explains the outage.
 * `auth` is injectable for tests.
 */
export async function initNav(container, { auth = getAuth() } = {}) {
  const { user, failed } = await pageUser(auth, null);

  clear(container);
  container.append(link("/", "Home"), link("/movies.html", "Movies"), link("/screenings.html", "Schedule"));
  if (user) {
    if (user.role === "CUSTOMER") {
      container.append(link("/bookings.html", "My Bookings"));
    }
    if (user.role === "ADMIN") {
      container.append(
        link("/admin-movies.html", "Movies (Admin)"),
        link("/admin-screenings.html", "Screenings (Admin)"),
        link("/admin-bookings.html", "All Bookings"),
      );
    }
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
  } else if (failed) {
    container.append(el("span", { className: "nav-user", text: "Account unavailable" }));
  } else {
    container.append(link("/login.html", "Log in"), link("/register.html", "Register"));
  }
}
