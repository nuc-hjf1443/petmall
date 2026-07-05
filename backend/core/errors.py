from enum import StrEnum

from fastapi import HTTPException, status


class ErrorCode(StrEnum):
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    SERVER_ERROR = "SERVER_ERROR"


class AppException(HTTPException):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


def bad_request(message: str) -> AppException:
    return AppException(ErrorCode.BAD_REQUEST, message, status.HTTP_400_BAD_REQUEST)


def unauthorized(message: str = "Unauthorized") -> AppException:
    return AppException(ErrorCode.UNAUTHORIZED, message, status.HTTP_401_UNAUTHORIZED)


def forbidden(message: str = "Forbidden") -> AppException:
    return AppException(ErrorCode.FORBIDDEN, message, status.HTTP_403_FORBIDDEN)


def not_found(message: str) -> AppException:
    return AppException(ErrorCode.NOT_FOUND, message, status.HTTP_404_NOT_FOUND)


def conflict(message: str) -> AppException:
    return AppException(ErrorCode.CONFLICT, message, status.HTTP_409_CONFLICT)


def rate_limited(message: str) -> AppException:
    return AppException(ErrorCode.RATE_LIMITED, message, status.HTTP_429_TOO_MANY_REQUESTS)
