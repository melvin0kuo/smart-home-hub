from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse


class HubError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def error_response(status: int, code: str, message: str):
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": uuid4().hex,
            }
        },
    )


async def hub_error_handler(request: Request, error: HubError):
    return error_response(error.status, error.code, error.message)
