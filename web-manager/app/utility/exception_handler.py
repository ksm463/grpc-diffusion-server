from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger = getattr(request.app.state, 'logger', logging.getLogger(__name__))

    if exc.status_code == 401:
        path = request.url.path
        accept_header = request.headers.get("accept", "")

        if path.startswith("/api/") or \
           path.startswith("/auth/") or \
           path == "/users/me" or \
           path == "/login" or \
           path == "/create_account" or \
           ("application/json" in accept_header and "text/html" not in accept_header.lower()):
            logger.warning(f"HTTP 401 Unauthorized for API or auth-related path: {path}. Client expects JSON. Detail: {exc.detail}")
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=getattr(exc, "headers", None),
            )
        else:
            logger.info(f"Unauthorized HTML page access to {path}, redirecting to /login. Detail: {exc.detail}")
            return RedirectResponse(url="/login", status_code=302)

    logger.error(f"HTTPException encountered: {exc.status_code} for path {request.url.path}. Detail: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )
