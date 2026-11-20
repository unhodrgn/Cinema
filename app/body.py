"""Reading JSON request bodies (shared by every API module)."""

from flask import request

from .errors import INVALID_JSON, UNSUPPORTED_MEDIA_TYPE, AppError


def json_body():
    """The request body as a JSON object (``dict``).

    * Not ``Content-Type: application/json``           -> 415 ``unsupported_media_type``
    * Empty, malformed, or not a JSON object            -> 400 ``invalid_json``
    * Larger than ``MAX_CONTENT_LENGTH``                -> 413 ``payload_too_large``

    Requiring the JSON content type on every write also means a cross-origin page cannot
    send one without a CORS preflight.
    """
    if request.mimetype != "application/json":
        raise AppError(UNSUPPORTED_MEDIA_TYPE)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise AppError(INVALID_JSON)
    return data
