from __future__ import annotations
from enum import Enum
from fastapi import HTTPException
from pydantic import BaseModel


class ErrorCode(str, Enum):
    UNAUTHORIZED         = "unauthorized"
    FORBIDDEN            = "forbidden"
    TASK_NOT_FOUND       = "task_not_found"
    TASK_ALREADY_DONE    = "task_already_done"
    INVALID_REQUEST      = "invalid_request"
    SERVER_BUSY          = "server_busy"
    INTERNAL_ERROR       = "internal_error"


_ERROR_MAP: dict[ErrorCode, tuple[int, str]] = {
    ErrorCode.UNAUTHORIZED:      (401, "API key is missing or invalid."),
    ErrorCode.FORBIDDEN:         (403, "You do not have permission to access this resource."),
    ErrorCode.TASK_NOT_FOUND:    (404, "Task not found."),
    ErrorCode.TASK_ALREADY_DONE: (409, "Task already completed."),
    ErrorCode.INVALID_REQUEST:   (422, "Invalid request format."),
    ErrorCode.SERVER_BUSY:       (503, "Server is busy. Please retry later."),
    ErrorCode.INTERNAL_ERROR:    (500, "Internal server error occurred."),
}


class ErrorDetail(BaseModel):
    code: str
    message: str
    param: str | None = None
    type: str = "gateway_error"


def gateway_error(
    code: ErrorCode,
    message: str | None = None,
    param: str | None = None,
) -> HTTPException:
    """ErrorCode → HTTPException. Used as raise gateway_error(...) in routes."""
    status_code, default_msg = _ERROR_MAP.get(code, (500, "Unknown error"))
    detail = ErrorDetail(
        code=code.value,
        message=message or default_msg,
        param=param,
    ).model_dump()
    return HTTPException(status_code=status_code, detail=detail)


def mcp_error(code: ErrorCode, message: str | None = None) -> dict:
    """Error dict for MCP tool returns."""
    _, default_msg = _ERROR_MAP.get(code, (500, "Unknown error"))
    return {
        "status": "error",
        "code": code.value,
        "message": message or default_msg,
    }
