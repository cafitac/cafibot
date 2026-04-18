from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .db import lookup_api_key
from .errors import ErrorCode, gateway_error

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    token = creds.credentials if creds else None
    if not token:
        raise gateway_error(ErrorCode.UNAUTHORIZED)
    user = await lookup_api_key(token)
    if user is None:
        raise gateway_error(ErrorCode.UNAUTHORIZED)
    return user
