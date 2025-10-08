import grpc
from grpc import aio as grpc_aio
import asyncio
import redis.asyncio as redis
import configparser
import os
import signal
import argparse
import multiprocessing
from loguru import logger
from functools import partial

from interface import diffusion_processing_pb2_grpc
from interface.diffusion_service import DiffusionProcessingServicer, create_worker_subprocess
from utility.logger import setup_logger
from process import ProcessLifecycleManager, create_watchdog_subprocess


async def run_server(config_path: str):
    """서버 설정 및 실행"""
    config = configparser.ConfigParser()
    config.read(config_path)

    # 로거 설정
    setup_logger(config_path)
    logger.info("="*10 + " gRPC Server Starting " + "="*10)

    # 프로세스 생명주기 관리자 초기화
    lifecycle_config = {
        'max_retries': int(config.get('PROCESS', 'MAX_STARTUP_RETRIES', fallback=10)),
        'initial_delay': float(config.get('PROCESS', 'INITIAL_DELAY', fallback=0.1)),
        'max_delay': float(config.get('PROCESS', 'MAX_DELAY', fallback=5.0)),
        'shutdown_timeout': float(config.get('PROCESS', 'SHUTDOWN_TIMEOUT', fallback=10.0)),
        'watchdog_check_interval': float(config.get('WATCHDOG', 'CHECK_INTERVAL', fallback=2.0)),
        'watchdog_max_restarts': int(config.get('WATCHDOG', 'MAX_RESTART_ATTEMPTS', fallback=3))
    }
    
    lifecycle_manager = ProcessLifecycleManager(lifecycle_config)
    server = None
    shutdown_event = asyncio.Event()
    
    # SIGTERM 핸들러 설정 (watchdog에서 보내는 신호 처리)
    def handle_sigterm(signum, frame):
        logger.warning(f"Received signal {signum}. Setting shutdown event.")
        shutdown_event.set()
    
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    try:
        # Redis 연결
        redis_client = await connect_to_redis(config)
        
        # 워커 프로세스 시작
        max_workers = int(config.get('STABLEDIFFUSION', 'MAX_WORKER', fallback=1))
        workers_started = await lifecycle_manager.start_workers(
            create_worker_fn=create_worker_subprocess,
            worker_count=max_workers,
            config_path=config_path,
            worker_type='StableDiffusion'
        )
        
        if not workers_started:
            raise SystemExit("Failed to start worker processes.")
        
        # Watchdog 프로세스 시작
        lifecycle_manager.start_watchdog(create_watchdog_subprocess)
        
        # gRPC 서버 시작
        server = await setup_grpc_server(config, redis_client)
        
        # 서버 실행 및 종료 대기
        await wait_for_shutdown(server, shutdown_event)
        
    except KeyboardInterrupt:
        logger.warning("Server stopping due to KeyboardInterrupt.")
    except Exception as e:
        logger.critical(f"A critical error occurred: {e}")
        logger.exception(e)
    finally:
        # 정리 작업
        await cleanup(server, lifecycle_manager)


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


async def cleanup(server: grpc_aio.Server, lifecycle_manager: ProcessLifecycleManager):
    """서버 종료 시 정리 작업"""
    logger.info("Initiating shutdown sequence...")
    
    # gRPC 서버 종료
    if server:
        await server.stop(grace=1)
        logger.info("gRPC server stopped.")
    
    # 프로세스 생명주기 관리자를 통한 정리
    await lifecycle_manager.shutdown()
    
    # 이벤트 루프 정리 전 약간의 지연
    await asyncio.sleep(0.5)
    logger.success("Shutdown complete.")


if __name__ == '__main__':
    # Multiprocessing 설정
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        print("Multiprocessing start method already set or 'spawn' not available.")

    # 인자 파싱
    parser = argparse.ArgumentParser(description='Image Processing Server')
    parser.add_argument(
        '--config',
        type=str,
        default='./ai_server_config.ini',
        help='Path to the configuration file'
    )
    args = parser.parse_args()

    # 서버 실행
    try:
        asyncio.run(run_server(args.config))
    except KeyboardInterrupt:
        logger.info("Server process interrupted by user.")