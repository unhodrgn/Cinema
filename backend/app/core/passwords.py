"""Password hashing for accounts (Werkzeug, one-way, salted).

New hashes use ``pbkdf2:sha256:600000``, the same method and cost as the hashes already in
``backend/seeds/demo.sql``. Using one method for every stored hash keeps verification time
uniform, which is what makes the dummy verification for unknown accounts a fair match.
``check_password_hash`` also verifies other Werkzeug methods (for example scrypt), so a
hash created elsewhere keeps working.

Technical limits only, no business password policy (BR-DL-001 section 6 approves none):

* ``USERNAME_MAX_LENGTH``  the width of ``users.username`` (``varchar(60)``).
* ``PASSWORD_MAX_LENGTH``  stops a request from making the server hash an arbitrarily long
                           string (the request body is already limited to 64 KiB).

This module imports only Werkzeug, so the setup script can use it without the web app.
"""

import secrets

from werkzeug.security import check_password_hash, generate_password_hash

PASSWORD_HASH_METHOD = "pbkdf2:sha256:600000"
USERNAME_MAX_LENGTH = 60
PASSWORD_MAX_LENGTH = 256

_dummy_hash = None


def hash_password(password):
    """A salted one-way hash of ``password`` for ``users.password_hash``."""
    return generate_password_hash(password, method=PASSWORD_HASH_METHOD)


def verify_password(stored_hash, password):
    """True if ``password`` matches ``stored_hash``. Never raises for a malformed hash."""
    try:
        return check_password_hash(stored_hash, password)
    except ValueError:  # unsupported or malformed hash method: the account cannot log in
        return False


def _get_dummy_hash():
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password(secrets.token_urlsafe(24))
    return _dummy_hash


def verify_against_dummy(password):
    """Spend the time of one real verification for an account that does not exist.

    Always returns False. Without it a login for an unknown account would answer much
    faster than one with a wrong password and reveal which account IDs exist.
    """
    check_password_hash(_get_dummy_hash(), password)
    return False
