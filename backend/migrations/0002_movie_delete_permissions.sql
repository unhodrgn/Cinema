-- Apply as the database owner to enable movie deletion with the Compose runtime role.
GRANT DELETE ON movies, showtimes TO cinema_api;
