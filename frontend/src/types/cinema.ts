export interface User {
  user_id: number;
  username: string;
  role: "ADMIN" | "CUSTOMER";
}
export interface Movie {
  movie_id: number;
  title: string;
  poster_url: string | null;
  duration_minutes: number;
  genre: string | null;
  rating: string | null;
  release_date: string | null;
  synopsis: string | null;
}
export interface Showtime {
  showtime_id: number;
  movie_id: number;
  title: string;
  poster_url: string | null;
  room_id: number;
  room_name: string;
  starts_at: string;
  ends_at: string;
  ticket_price: string;
  has_started: boolean;
  has_bookings?: boolean;
}
export interface Seat {
  seat_id: number;
  seat_row: string;
  seat_number: number;
}
export interface AvailableSeat extends Seat {
  is_available: boolean;
}
export interface Booking {
  booking_id: number;
  user_id: number;
  username?: string;
  showtime_id: number;
  title: string;
  poster_url: string | null;
  room_name: string;
  starts_at: string;
  ends_at: string;
  total_amount: string;
  status: "BOOKED" | "CANCELLED" | "EXPIRED";
  payment_status: "UNPAID" | "PAID";
  booked_at: string;
  expires_at: string;
  paid_at: string | null;
  cancelled_at: string | null;
  seats: Seat[];
}
export interface Schedule {
  date: string;
  screenings: Showtime[];
}
