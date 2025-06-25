from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []

    for error in exc.errors():
        msg = error.get("msg", "")

        if ',' in msg:
            msg = msg.split(',', 1)[1].strip()

        errors.append(msg)

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": errors[0] if errors else "Validation error",
            "data": errors,
        }
    )
