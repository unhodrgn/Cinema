from app.core.errors import ValidationError

MAX_SEATS_PER_BOOKING = 50


def booking_request(body):
    problems = {}

    screening_id = body.get("screening_id")
    if screening_id is None or isinstance(screening_id, bool) or not isinstance(screening_id, int):
        problems["screening_id"] = "A valid positive screening ID is required."
    elif screening_id <= 0 or screening_id >= 2**63:
        problems["screening_id"] = "A valid positive screening ID is required."

    raw_seats = body.get("seat_ids")
    if not isinstance(raw_seats, list) or len(raw_seats) == 0:
        problems["seat_ids"] = "At least one seat must be selected."
    elif len(raw_seats) > MAX_SEATS_PER_BOOKING:
        problems["seat_ids"] = f"Cannot book more than {MAX_SEATS_PER_BOOKING} seats in a single booking."
    else:
        seat_ids = []
        has_invalid = False
        for s in raw_seats:
            if isinstance(s, bool) or not isinstance(s, int) or s <= 0 or s >= 2**63:
                has_invalid = True
                break
            seat_ids.append(s)
        if has_invalid:
            problems["seat_ids"] = "All seat IDs must be positive integers."
        elif len(seat_ids) != len(set(seat_ids)):
            problems["seat_ids"] = "Seat list contains duplicates."

    if problems:
        raise ValidationError(problems)

    return screening_id, seat_ids
