def public_user(row):
    """The only user fields the API ever returns. Never the password hash."""
    return {"user_id": row["user_id"], "username": row["username"], "role": row["role"]}
