"""Registration-only validation. Login still uses its historical normalization."""
import re
import unicodedata

from app.core.passwords import USERNAME_MAX_LENGTH
from app.core.username_policy_data import EMAIL, LETTER_DIGIT, RAW_CLASS

_RAW = re.compile(f"[{RAW_CLASS}]+")
_START = re.compile(f"[{LETTER_DIGIT}]")
_PLAIN = re.compile(f"[{LETTER_DIGIT}][{LETTER_DIGIT}_.+-]*")
_EMAIL = re.compile(EMAIL)


def registration_username(raw):
    """Return (canonical ID, field error). The input is never trimmed."""
    if raw is None or raw == "":
        return None, "Account ID is required."
    if not isinstance(raw, str):
        return None, "Account ID must be text."
    if not _RAW.fullmatch(raw):
        return None, "Account ID contains a space, invisible character, or unsupported character."
    if not _START.match(raw):
        return None, "Start with a letter or digit and use only letters, digits, _, -, ., or +."
    value = unicodedata.normalize("NFKC", raw)
    if len(value) > USERNAME_MAX_LENGTH:
        return None, f"Account ID must be at most {USERNAME_MAX_LENGTH} characters after normalization."
    if "@" in value:
        if not _EMAIL.fullmatch(value):
            return None, "Enter a valid email address to use as your account ID."
    elif not _PLAIN.fullmatch(value):
        return None, "Start with a letter or digit and use only letters, digits, _, -, ., or +."
    return value, None
