"""서버 초기화 및 설정 관련 유틸리티"""

import grpc
from grpc import aio as grpc_aio
import asyncio
import redis.asyncio as redis
import configparser
from loguru import logger

from interface import diffusion_processing_pb2_grpc
from interface.diffusion_service import DiffusionProcessingServicer
from .lifecycle import ProcessLifecycleManager


async def connect_to_redis(config: configparser.ConfigParser) -> redis.Redis:
    """Redis 연결 설정"""
    redis_use_uds = config.getboolean('REDIS', 'USE_UDS')
    redis_db = int(config['REDIS']['DB'])

    if redis_use_uds:
        redis_uds_path = config.get('REDIS', 'UDS_PATH')
        logger.info(f"Connecting to Redis UDS at {redis_uds_path}")
        redis_client = redis.Redis(unix_socket_path=redis_uds_path, db=redis_db)
    else:
        redis_host = config.get('REDIS', 'HOST')
        redis_port = int(config.get('REDIS', 'PORT'))
        logger.info(f"Connecting to Redis at {redis_host}:{redis_port}")
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=False
        )
    
    await redis_client.ping()
    logger.success("Successfully connected to Redis.")
    return redis_client


async def setup_grpc_server(
    config: configparser.ConfigParser,
    redis_client: redis.Redis
) -> grpc_aio.Server:
    """gRPC 서버 설정 및 시작"""
    grpc_port = int(config['GRPC']['PORT'])
    message_length = int(config['GRPC']['MAX_MESSAGE_LENGTH'])
    options = [
        ('grpc.max_send_message_length', message_length),
        ('grpc.max_receive_message_length', message_length),
    ]
    
    server = grpc_aio.server(options=options)
    
    # Servicer 생성 및 추가
    queue_key = config.get('STABLEDIFFUSION', 'QUEUE_KEY')
    result_key_prefix = config.get('STABLEDIFFUSION', 'RESULT_KEY_PREFIX')
    result_channel_prefix = config.get('STABLEDIFFUSION', 'RESULT_CHANNEL_PREFIX')
    processing_timeout = int(config.get('STABLEDIFFUSION', 'TIMEOUT'))

    servicer = DiffusionProcessingServicer(
        redis_client=redis_client,
        queue_key=queue_key,
        result_key_prefix=result_key_prefix,
        result_channel_prefix=result_channel_prefix,
        processing_timeout=processing_timeout,
    )
    
    diffusion_processing_pb2_grpc.add_ImageGeneratorServicer_to_server(servicer, server)
    server.add_insecure_port(f'[::]:{grpc_port}')
    
    await server.start()
    logger.success(f"gRPC server started on port {grpc_port}. Waiting for requests...")
    
    return server


async def wait_for_shutdown(server: grpc_aio.Server, shutdown_event: asyncio.Event):
    """서버 종료 대기"""
    server_task = asyncio.create_task(server.wait_for_termination())
    shutdown_task = asyncio.create_task(shutdown_event.wait())
    
    done, pending = await asyncio.wait(
        [server_task, shutdown_task],
        return_when=asyncio.FIRST_COMPLETED
    )
    
    # 완료되지 않은 태스크 취소
    for task in pending:
        task.cancel()
    
    if shutdown_event.is_set():
        logger.warning("Shutdown event triggered by watchdog. Initiating graceful shutdown...")
        await server.stop(grace=5)


async def cleanup_redis(redis_client: redis.Redis):
    """Redis 연결 정리"""
    if redis_client:
        try:
            await redis_client.close()
            logger.info("Redis connection closed.")
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {e}")


async def cleanup_partial(
    redis_client: redis.Redis,
    server: grpc_aio.Server,
    lifecycle_manager: ProcessLifecycleManager
):
    """부분 정리 작업 (워커/watchdog 포함)"""
    logger.info("Initiating partial cleanup...")
    
    # gRPC 서버 종료
    if server:
        try:
            await server.stop(grace=1)
            logger.info("gRPC server stopped.")
        except Exception as e:
            logger.warning(f"Error stopping gRPC server: {e}")
    
    # 프로세스 생명주기 관리자를 통한 정리
    try:
        await lifecycle_manager.shutdown()
    except Exception as e:
        logger.warning(f"Error during lifecycle manager shutdown: {e}")
    
    # Redis 연결 정리
    await cleanup_redis(redis_client)
    
    logger.info("Partial cleanup complete.")


async def cleanup_all(
    server: grpc_aio.Server,
    redis_client: redis.Redis,
    lifecycle_manager: ProcessLifecycleManager
):
    """전체 정리 작업"""
    logger.info("Initiating shutdown sequence...")
    
    # gRPC 서버 종료
    if server:
        try:
            await server.stop(grace=1)
            logger.info("gRPC server stopped.")
        except Exception as e:
            logger.warning(f"Error stopping gRPC server: {e}")
    
    # 프로세스 생명주기 관리자를 통한 정리
    try:
        await lifecycle_manager.shutdown()
    except Exception as e:
        logger.warning(f"Error during lifecycle manager shutdown: {e}")
    
    # Redis 연결 정리
    await cleanup_redis(redis_client)
    
    # 이벤트 루프 정리 전 약간의 지연
    await asyncio.sleep(0.5)
    logger.success("Shutdown complete.")