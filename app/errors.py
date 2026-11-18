from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from datetime import datetime, timezone


def _body(status: int, message: str, details=None):
    body = {"status": status, "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()}
    if details is not None:
        body["details"] = details
    return body


class ConflictoError(Exception):
    """Regla de negocio que no se cumple (409). Puede traer prendas parecidas en details."""

    def __init__(self, message: str, details=None):
        super().__init__(message)
        self.message = message
        self.details = details


def register_error_handlers(app: FastAPI):
    @app.exception_handler(ConflictoError)
    async def conflict_error(request: Request, exc: ConflictoError):
        return JSONResponse(status_code=409, content=_body(409, exc.message, exc.details))

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code,
                            content=_body(exc.status_code, str(exc.detail)))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # jsonable: los errores pueden traer objetos que no son JSON
        details = [{"field": ".".join(str(p) for p in e["loc"]), "problem": e["msg"]}
                   for e in exc.errors()]
        return JSONResponse(status_code=422,
                            content=_body(422, "Invalid data", details))

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        # No mostramos el error interno al cliente.
        return JSONResponse(status_code=500,
                            content=_body(500, "Internal server error"))
