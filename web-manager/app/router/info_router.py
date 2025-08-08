from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pathlib import Path
import os

from utility.request import get_manager_config, get_server_config, get_logger


info_router = APIRouter()


@info_router.get("/api/info/host_system_info")
async def get_host_system_information(request: Request, logger=Depends(get_logger)):
    # logger.debug(f"Client {request.client.host}: Requested host system information.")

    host_ip = os.getenv("HOST_IP", "N/A")
    host_os_version = os.getenv("HOST_OS_VERSION", "N/A (Ubuntu 24 expected)")
    host_timezone = os.getenv("HOST_TIMEZONE", "N/A")
    
    logger.info(f"Host Info - IP: {host_ip}, OS: {host_os_version}, Timezone: {host_timezone}")

    return JSONResponse(content={
        "host_ip_address": host_ip,
        "host_os_version": host_os_version,
        "host_timezone": host_timezone
    })

@info_router.get("/api/info/client_ip")
async def get_client_ip_address(request: Request, logger=Depends(get_logger)):
    client_ip = request.client.host
    logger.info(f"Client {client_ip}: Requested client IP address. Returning: {client_ip}")
    return JSONResponse(content={"client_ip": client_ip})

@info_router.get("/api/info/grpc_info")
async def get_dummy_info_info(request: Request, server_config = Depends(get_server_config), logger=Depends(get_logger)):
    logger.debug("Serving grpc port data for /api/info/grpc_info")
    
    proto_file_path_str = server_config['grpc']['port']

    dummy_grpc_port = proto_file_path_str
    dummy_status = "Running (Temporary Data)"

    return JSONResponse(content={
        "grpc_port": dummy_grpc_port,
        "server_status": dummy_status,
        "message": "This is temporary data. Real implementation needed."
    })


@info_router.get("/api/info/proto", response_class=PlainTextResponse)
async def get_proto_content(
    server_config = Depends(get_server_config),
    logger = Depends(get_logger)
):
    if not server_config or 'GLOBAL' not in server_config or 'PROTO_BUFF_PATH' not in server_config['GLOBAL']:
        logger.error("Configuration error: PROTO_BUFF_PATH not found in grpc config['GLOBAL']")
        raise HTTPException(status_code=500, detail="Server configuration error: PROTO_BUFF_PATH is not set.")

    proto_file_path_str = server_config['GLOBAL']['PROTO_BUFF_PATH']
    proto_file_path = Path(proto_file_path_str)

    logger.info(f"Attempting to read PROTO file from: {proto_file_path}")

    if not proto_file_path.exists():
        logger.error(f"PROTO file not found at path: {proto_file_path}")
        raise HTTPException(status_code=404, detail="PROTO file not found at the configured path.")

    if not proto_file_path.is_file():
        logger.error(f"Path exists but is not a file: {proto_file_path}")
        raise HTTPException(status_code=400, detail="Configured PROTO path points to a directory, not a file.")

    try:
        content = proto_file_path.read_text(encoding='utf-8')
        logger.info(f"Successfully read PROTO file: {proto_file_path.name}")
        return PlainTextResponse(content=content, headers={"Cache-Control": "no-store"})
    except Exception as exc:
        logger.error(f"Error reading PROTO file {proto_file_path}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error reading PROTO file: {exc}")
