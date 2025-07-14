from enum import Enum

class ResponseStatus(Enum):
    SUCCESS = 200
    DISCARD = 300
    UNAUTHORIZED = 401
    NOT_FOUND = 404
    INVALID = 409
    SERVER_ERROR = 500