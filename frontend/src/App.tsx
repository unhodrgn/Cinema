import { useEffect } from "react";
import { Navbar, SessionProvider } from "./components/common/Navbar";
import { HomePage, MoviesPage } from "./pages/HomePage";
import { MovieDetailPage } from "./pages/MovieDetailPage";
import { ShowtimeSelector } from "./features/showtimes/ShowtimeSelector";
import { LoginForm } from "./features/auth/LoginForm";
import { BookingPage } from "./pages/BookingPage";
import { CheckoutPage } from "./pages/CheckoutPage";
import { MyBookingsPage } from "./pages/MyBookingsPage";
import { AdminDashboard } from "./pages/AdminDashboard";

const pages = {
  index: ["Cinema Reservation", <HomePage />],
  movies: ["Movies", <MoviesPage />],
  movie: ["Movie Details", <MovieDetailPage />],
  screenings: [
    "Screening Schedule",
    <>
      <h1>Screening Schedule</h1>
      <ShowtimeSelector />
    </>,
  ],
  seats: ["Select Seats", <BookingPage />],
  booking: ["Booking Details", <CheckoutPage />],
  bookings: ["My Bookings", <MyBookingsPage />],
  login: ["Log in", <LoginForm />],
  register: ["Register", <LoginForm register />],
  "admin-movies": ["Manage Movies", <AdminDashboard section="movies" />],
  "admin-screenings": [
    "Manage Screenings",
    <AdminDashboard section="screenings" />,
  ],
  "admin-bookings": ["All Bookings", <AdminDashboard section="bookings" />],
} as const;
export function App() {
  const name = location.pathname.slice(1).replace(/\.html$/, "") || "index";
  const page = pages[name as keyof typeof pages];
  useEffect(() => {
    document.title = page
      ? page[0] + " — Cinema Reservation"
      : "Page not found";
    document.body.classList.toggle("admin", name.startsWith("admin-"));
  }, [name, page]);
  return (
    <SessionProvider>
      <Navbar />
      <main className="container">{page?.[1] || <h1>Page not found</h1>}</main>
      <footer className="site-footer">
        Movie posters: TMDB. This product uses the TMDB API but is not endorsed
        or certified by TMDB.
      </footer>
    </SessionProvider>
  );
}
