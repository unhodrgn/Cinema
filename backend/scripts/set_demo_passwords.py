"""Set known passwords for existing accounts (setup only, never part of the running API).

The seeded accounts (``admin``, ``customer1``, ``customer2``) come with alphanumeric demo
passwords hashed in ``backend/seeds/demo.sql``. Run this script whenever you want to replace
their passwords. It needs a database role that may UPDATE ``users``; the role the API
runs as does not and must not have that permission (integration contract, section 8).

Connection: explicit ``SETUP_DB_*`` environment variables ONLY. There is no fallback to
``DB_*`` (the API's runtime credentials), no default host or port, and the script never
reads the API's configuration or ``.env``. Set them in the terminal that runs the script:

    SETUP_DB_HOST      required, e.g. 127.0.0.1
    SETUP_DB_PORT      required
    SETUP_DB_NAME      required: the database to change
    SETUP_DB_USER      required: a role that may UPDATE users
    SETUP_DB_PASSWORD  optional (without it libpq may still use PGPASSWORD or ~/.pgpass)

The new password is asked for with a hidden prompt (twice). For automation it can be given
in ``SETUP_NEW_PASSWORD`` instead; never put a password on the command line or in a file.

    python backend/scripts/set_demo_passwords.py --username admin --username customer1

It prints the target and asks you to type the database name to confirm (``--yes`` skips the
question). Only ``users.password_hash`` of the named, EXISTING accounts is updated, in one
transaction: if any name is unknown nothing is changed. Neither the password nor a hash is
ever printed or logged. The script creates no roles and changes no permissions.

Exit codes: 0 done, 1 nothing changed (unknown account, refused, database error),
2 bad configuration or input.
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.passwords import PASSWORD_MAX_LENGTH, hash_password  # noqa: E402  (Werkzeug only)

REQUIRED = ("SETUP_DB_HOST", "SETUP_DB_PORT", "SETUP_DB_NAME", "SETUP_DB_USER")


class SetupError(Exception):
    """Bad configuration or input (exit code 2). The message is safe to print."""


def read_target(environ):
    """The explicit setup connection parameters, or raise ``SetupError``."""
    values = {name: (environ.get(name) or "").strip() for name in REQUIRED}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise SetupError(
            "missing " + ", ".join(missing) + ". The setup tool uses only explicit SETUP_DB_* "
            "settings and never falls back to the application's DB_* credentials."
        )
    try:
        port = int(values["SETUP_DB_PORT"])
    except ValueError:
        raise SetupError("SETUP_DB_PORT must be an integer") from None
    if not 1 <= port <= 65535:
        raise SetupError("SETUP_DB_PORT must be between 1 and 65535")
    target = {
        "host": values["SETUP_DB_HOST"],
        "port": port,
        "dbname": values["SETUP_DB_NAME"],
        "user": values["SETUP_DB_USER"],
        "connect_timeout": 5,
        "application_name": "cinema_setup",
    }
    password = environ.get("SETUP_DB_PASSWORD")
    if password:
        target["password"] = password
    return target


def stdin_is_a_terminal():
    """True only when a person can really type here.

    ``isatty()`` is not enough on Windows: it reports True for the ``NUL`` device, and
    ``getpass`` then waits for a keyboard that is not there. ``GetConsoleMode`` succeeds
    only for a real console handle.
    """
    if not sys.stdin or not sys.stdin.isatty():
        return False
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
        mode = ctypes.c_uint32()
        return bool(kernel32.GetConsoleMode(handle, ctypes.byref(mode)))
    return True


def read_new_password(environ):
    """The new password from SETUP_NEW_PASSWORD or a confirmed hidden prompt."""
    password = environ.get("SETUP_NEW_PASSWORD")
    if not password:
        # Only prompt when a person is actually there; never wait on a redirected stdin.
        if not stdin_is_a_terminal():
            raise SetupError("no password given (set SETUP_NEW_PASSWORD or run in a terminal)")
        try:
            password = getpass.getpass("New password: ")
            if password != getpass.getpass("Repeat the new password: "):
                raise SetupError("the two passwords are not the same")
        except (EOFError, KeyboardInterrupt):
            raise SetupError("no password given (set SETUP_NEW_PASSWORD or run in a terminal)") from None
    if not password:
        raise SetupError("the password must not be empty")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise SetupError(f"the password must be at most {PASSWORD_MAX_LENGTH} characters")
    return password


def confirm(target, assume_yes):
    print(f"Target: database {target['dbname']!r} on {target['host']}:{target['port']} as {target['user']!r}")
    if assume_yes:
        return True
    try:
        typed = input("Type the database name to confirm: ").strip()
    except EOFError:
        return False
    return typed == target["dbname"]


def set_passwords(target, usernames, password_hash):
    """Update the named accounts in one transaction; return the names or raise ``LookupError``."""
    connection = psycopg2.connect(**target)
    try:
        with connection:  # one transaction: commit at the end, rollback on any error
            with connection.cursor() as cur:
                for username in usernames:
                    cur.execute(
                        "UPDATE users SET password_hash = %s WHERE username = %s RETURNING user_id",
                        (password_hash, username),
                    )
                    if cur.fetchone() is None:
                        raise LookupError(username)
    finally:
        connection.close()


def build_parser():
    parser = argparse.ArgumentParser(description="Set known passwords for existing accounts (setup only).")
    parser.add_argument("--username", action="append", required=True, metavar="ACCOUNT_ID",
                        help="an existing account ID; repeat for several accounts")
    parser.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    return parser


def main(argv=None, environ=None):
    args = build_parser().parse_args(argv)
    environ = os.environ if environ is None else environ
    try:
        target = read_target(environ)
        usernames = list(dict.fromkeys(args.username))
        if any(not name.strip() for name in usernames):
            raise SetupError("account IDs must not be empty")
        password = read_new_password(environ)
    except SetupError as error:
        print(f"set_demo_passwords: {error}", file=sys.stderr)
        return 2

    if not confirm(target, args.yes):
        print("set_demo_passwords: not confirmed, nothing changed.", file=sys.stderr)
        return 1
    try:
        set_passwords(target, usernames, hash_password(password))
    except LookupError as error:
        print(f"set_demo_passwords: no account named {error.args[0]!r}; nothing was changed.", file=sys.stderr)
        return 1
    except psycopg2.Error as error:
        # Only the SQLSTATE: the driver's text can name hosts and users.
        print(f"set_demo_passwords: database error (SQLSTATE {error.pgcode}); nothing was changed.",
              file=sys.stderr)
        return 1
    print("Password updated for: " + ", ".join(usernames))
    return 0


if __name__ == "__main__":
    sys.exit(main())
