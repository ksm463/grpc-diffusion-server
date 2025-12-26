from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pathlib import Path
import os

from database.info_schemas import HostSystemInfo, ClientIPResponse, GrpcInfoResponse
from utility.request import get_server_config, get_manager_config, get_logger


info_router = APIRouter()


@info_router.get(
    "/api/info/host_system_info",
    response_model=HostSystemInfo,
    tags=["info"]
)
async def get_host_system_information(request: Request, logger=Depends(get_logger)):
    """
    호스트 시스템 정보 조회

    서버의 IP 주소, OS 버전, 타임존 정보를 반환합니다.
    """
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

@info_router.get(
    "/api/info/client_ip",
    response_model=ClientIPResponse,
    tags=["info"]
)
async def get_client_ip_address(request: Request, logger=Depends(get_logger)):
    """
    클라이언트 IP 주소 조회

    요청한 클라이언트의 IP 주소를 반환합니다.
    """
    client_ip = request.client.host
    logger.info(f"Client {client_ip}: Requested client IP address. Returning: {client_ip}")
    return JSONResponse(content={"client_ip": client_ip})

@info_router.get(
    "/api/info/grpc_info",
    response_model=GrpcInfoResponse,
    tags=["info"]
)
async def get_dummy_info_info(request: Request, server_config = Depends(get_server_config), logger=Depends(get_logger)):
    """
    gRPC 서버 정보 조회

    AI 서버의 gRPC 포트 번호와 작동 상태를 반환합니다.
    """
    logger.debug("Serving grpc port data for /api/info/grpc_info")
    
    grpc_port = server_config['grpc']['port']
    status = "Running (Temporary Data)"

    return JSONResponse(content={
        "grpc_port": grpc_port,
        "server_status": status,
        "message": "This is temporary data. Real implementation needed."
    })


@info_router.get(
    "/api/info/proto",
    response_class=PlainTextResponse,
    tags=["info"]
)
async def get_proto_content(
    manager_config = Depends(get_manager_config),
    logger = Depends(get_logger)
):
    """
    gRPC Protocol Buffer 정의 파일 조회

    diffusion_processing.proto 파일의 내용을 반환합니다.

    이 proto 파일은 이미지 생성을 위한 gRPC 인터페이스를 정의합니다:
    - Service: ImageGenerator
    - RPC: GenerateImage
    - Messages: GenerationRequest, GenerationResponse

    다른 언어로 gRPC 클라이언트 스텁을 생성할 때 사용할 수 있습니다.
    """
    if not manager_config or 'ENV' not in manager_config or 'PROTO_BUFF_PATH' not in manager_config['ENV']:
        logger.error("Configuration error: PROTO_BUFF_PATH not found in manager_config['ENV']")
        raise HTTPException(status_code=500, detail="Server configuration error: PROTO_BUFF_PATH is not set.")

    proto_file_path_str = manager_config['ENV']['PROTO_BUFF_PATH']
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
