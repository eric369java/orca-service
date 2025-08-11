from enum import Enum

class ResponseStatus(int, Enum):
    SUCCESS = 200
    UNAUTHORIZED = 401
    NOT_FOUND = 404
    INVALID = 409
    EXPIRED = 400
    SERVER_ERROR = 500