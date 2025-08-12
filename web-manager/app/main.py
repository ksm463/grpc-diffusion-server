from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
import uvicorn
from prometheus_fastapi_instrumentator import Instrumentator
from pathlib import Path
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.config import manager_config
from core.lifespan import lifespan
from core.exception_handler import custom_http_exception_handler

from router.info_router import info_router
from router.page_router import page_router
from router.image_router import image_router
from router.account_router import account_router


app = FastAPI(lifespan=lifespan)

@app.exception_handler(StarletteHTTPException)
async def call_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return await custom_http_exception_handler(request, exc)

@app.middleware("http")
async def suppress_devtools_404_middleware(request: Request, call_next):
    """
    개발자 도구 404 오류 로그를 제거하는 미들웨어
    """
    if request.url.path == "/.well-known/appspecific/com.chrome.devtools.json":
        return Response(status_code=204)
    
    response = await call_next(request)
    return response

instrumentator = Instrumentator(
    excluded_handlers=["/metrics", "/preview", "/docs", "/openapi.json"]
)
instrumentator.instrument(app).expose(app, include_in_schema=False, endpoint="/metrics")

static_dir_app_path = Path("/web-manager/app/web/static")
app.mount("/web/static", StaticFiles(directory=static_dir_app_path), name="static_app_files")

preview_dir_path = Path("/web-manager/preview")
app.mount("/preview", StaticFiles(directory=preview_dir_path), name="preview_files")


app.include_router(info_router)
app.include_router(page_router)
app.include_router(image_router)
app.include_router(account_router)


if __name__== "__main__":
    host = manager_config['ADDRESS']['HOST']
    port = manager_config['ADDRESS']['PORT']
    uvicorn.run("main:app", host=host, port=int(port), reload=True)
