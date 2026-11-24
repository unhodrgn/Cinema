import { RequireUser } from "../components/common/Navbar";
import { AdminMovies } from "../features/admin/AdminMovies";
import { AdminShowtimes } from "../features/admin/AdminShowtimes";
import { AdminBookings } from "../features/admin/AdminBookings";

export function AdminDashboard({
  section,
}: {
  section: "movies" | "screenings" | "bookings";
}) {
  const Page = {
    movies: AdminMovies,
    screenings: AdminShowtimes,
    bookings: AdminBookings,
  }[section];
  return (
    <RequireUser admin>
      <Page />
    </RequireUser>
  );
}
