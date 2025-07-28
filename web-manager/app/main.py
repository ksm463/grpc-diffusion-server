from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
import uvicorn
from prometheus_fastapi_instrumentator import Instrumentator
import configparser
from contextlib import asynccontextmanager
from pathlib import Path
from starlette.exceptions import HTTPException as StarletteHTTPException

from router.get_router import get_router
from router.page_router import page_router
from router.post_router import post_router
from router.account_router import account_router
from utility.logger import setup_logger
from utility.exception_handler import custom_http_exception_handler


manager_config_path = "/web-manager/app/manager_config.ini"
manager_config = configparser.ConfigParser()
manager_config.read(manager_config_path)

server_config_path = "/web-manager/ai-server/server_config.ini"
server_config = configparser.ConfigParser()
server_config.read(server_config_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_path = manager_config['ENV']['LOG_PATH']
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    logger = setup_logger(log_path)
    logger.info("Logging server started")
    logger.info(f"config info : {log_path}")
    
    app.state.manager_config = manager_config
    app.state.server_config = server_config
    app.state.logger = logger

    yield
    logger.info("Logging server stopped")


app = FastAPI(lifespan=lifespan)

@app.exception_handler(StarletteHTTPException)
async def call_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return await custom_http_exception_handler(request, exc)

instrumentator = Instrumentator(
    excluded_handlers=[
        "/metrics", 
        "/preview", 
        "/docs",
        "/openapi.json"
    ]
)

instrumentator.instrument(app)
instrumentator.expose(
    app,
    include_in_schema=False,
    endpoint="/metrics"
)

static_dir_app_path = Path("/web-manager/app/web/static")
app.mount("/web/static", StaticFiles(directory=static_dir_app_path), name="static_app_files")


app.include_router(page_router)
app.include_router(get_router)
app.include_router(post_router)
app.include_router(account_router)


if __name__== "__main__":
    host = manager_config['ADDRESS']['HOST']
    port = manager_config['ADDRESS']['PORT']
    uvicorn.run("main:app", host=host, port=int(port), reload=True)
