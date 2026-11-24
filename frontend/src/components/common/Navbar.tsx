import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { auth, errorMessage } from "../../services/apiClient";
import type { User } from "../../types/cinema";
import { loginUrl } from "../../../js/auth.js";

type Session = { user?: User | null; error?: string };
const SessionContext = createContext<Session>({});
export const useSession = () => useContext(SessionContext);
export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session>({});
  useEffect(() => {
    let active = true;
    auth
      .currentUser()
      .then((user) => active && setSession({ user }))
      .catch((error) => active && setSession({ error: errorMessage(error) }));
    return () => {
      active = false;
    };
  }, []);
  return (
    <SessionContext.Provider value={session}>
      {children}
    </SessionContext.Provider>
  );
}
export function RequireUser({
  admin = false,
  children,
}: {
  admin?: boolean;
  children: ReactNode;
}) {
  const { user, error } = useSession();
  useEffect(() => {
    if (user === null)
      location.assign(loginUrl(location.pathname + location.search));
  }, [user]);
  if (error) return <p role="alert">{error}</p>;
  if (!user) return <p role="status">Loading account…</p>;
  if (admin && user.role !== "ADMIN")
    return <p role="alert">Administrator access is required.</p>;
  return children;
}
export function Navbar() {
  const { user, error } = useSession();
  const links = [
    ["/", "Home"],
    ["/movies.html", "Movies"],
    ["/screenings.html", "Schedule"],
  ];
  if (user?.role === "CUSTOMER") links.push(["/bookings.html", "My Bookings"]);
  if (user?.role === "ADMIN")
    links.push(
      ["/admin-movies.html", "Movies (Admin)"],
      ["/admin-screenings.html", "Screenings (Admin)"],
      ["/admin-bookings.html", "All Bookings"],
    );
  if (user === null)
    links.push(["/login.html", "Log in"], ["/register.html", "Register"]);
  return (
    <header className="site-header">
      <a className="brand" href="/">
        Cinema Reservation
      </a>
      <nav id="site-nav" className="site-nav" aria-label="Main">
        {links.map(([href, label]) => (
          <a
            className="nav-link"
            key={href}
            href={href}
            aria-current={
              href === location.pathname ||
              (href === "/" && location.pathname === "/index.html")
                ? "page"
                : undefined
            }
          >
            {label}
          </a>
        ))}
        {user && (
          <>
            <span className="nav-user">
              {user.username} ({user.role})
            </span>
            <button
              className="nav-button"
              onClick={async () => {
                await auth.logout();
                location.assign("/");
              }}
            >
              Log out
            </button>
          </>
        )}
        {error && <span className="nav-user">Account unavailable</span>}
      </nav>
    </header>
  );
}
