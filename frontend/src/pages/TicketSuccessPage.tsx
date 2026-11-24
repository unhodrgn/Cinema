import type { Booking } from "../types/cinema";
export function TicketSuccessPage({ booking }: { booking: Booking }) {
  return (
    <p className="message message-success" role="status">
      Payment confirmed for booking #{booking.booking_id}.
    </p>
  );
}
