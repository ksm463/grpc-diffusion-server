from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from service.auth_service import get_current_user
from utility.request import get_logger

page_router = APIRouter()

templates = Jinja2Templates(directory="/web-manager/app/web/templates")

@page_router.get("/", include_in_schema=False, dependencies=[Depends(get_current_user)])
async def root_redirect(request: Request, logger = Depends(get_logger)):
    logger.info(f"Accessed studio page. Request method: {request.method}")
    return templates.TemplateResponse("studio.html", {"request": request, "user": None})

@page_router.get("/login", response_class=HTMLResponse)
async def load_login_page(request: Request, logger = Depends(get_logger)):
    logger.info(f"Received login page load request: {request.method}")
    return templates.TemplateResponse("users/login.html", {"request": request})

@page_router.get("/create_account", response_class=HTMLResponse)
async def load_create_account_page(request: Request, logger = Depends(get_logger)):
    logger.info(f"Received create_account page load request: {request.method}")
    return templates.TemplateResponse("users/create_account.html", {"request": request, "user": None})

@page_router.get("/info", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def load_info_page(request: Request, logger = Depends(get_logger)):
    logger.info(f"Accessed info page. Request method: {request.method}")
    return templates.TemplateResponse("info.html", {"request": request, "user": None})

@page_router.get("/studio", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def load_test_page(request: Request, logger = Depends(get_logger)):
    logger.info(f"Received studio page load request: {request.method}")
    return templates.TemplateResponse("studio.html", {"request": request, "user": None})

@page_router.get("/gallery", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def load_gallery_page(request: Request, logger = Depends(get_logger)):
    logger.info(f"Received gallery page load request: {request.method}")
    return templates.TemplateResponse("gallery.html", {"request": request, "user": None})

@page_router.get("/user_manage", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def load_user_manage_page(request: Request, logger = Depends(get_logger)):
    logger.info(f"Received user_manage page load request: {request.method}")
    return templates.TemplateResponse("users/user_manage.html", {"request": request, "user": None})

@page_router.get("/status/fastapi", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def load_fastapi_status_page(request: Request, logger = Depends(get_logger)):
    logger.info(f"Received FastAPI status page load request: {request.method} from {request.client.host}")
    return templates.TemplateResponse("status/fastapi_status.html", {"request": request, "user": None})

@page_router.get("/status/cpu", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def load_cpu_status_page(request: Request, logger = Depends(get_logger)):
    logger.info(f"Received CPU status page load request: {request.method} from {request.client.host}")
    return templates.TemplateResponse("status/cpu_status.html", {"request": request, "user": None})

@page_router.get("/status/gpu", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def load_gpu_status_page(request: Request, logger = Depends(get_logger)):
    logger.info(f"Received GPU status page load request: {request.method} from {request.client.host}")
    return templates.TemplateResponse("status/gpu_status.html", {"request": request, "user": None})
