"""Room choices included in the screening management response."""

from app.models.cinema import Room


def list_rooms(cur) -> list[Room]:
    cur.execute("SELECT room_id, room_name FROM theater_rooms ORDER BY room_id ASC")
    return [Room(room_id=row["room_id"], room_name=row["room_name"]) for row in cur.fetchall()]
