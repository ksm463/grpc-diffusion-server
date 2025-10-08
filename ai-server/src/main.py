import grpc
import asyncio
import redis.asyncio as redis
import configparser
import signal
import argparse
import multiprocessing
from loguru import logger

from interface.diffusion_service import create_worker_subprocess
from utility.logger import setup_logger
from process import ProcessLifecycleManager, create_watchdog_subprocess
from process.server_setup import (
    connect_to_redis,
    setup_grpc_server,
    wait_for_shutdown,
    cleanup_redis,
    cleanup_partial,
    cleanup_all
)


async def run_server(config_path: str):
    """서버 설정 및 실행"""
    # Config 읽기 및 로거 설정 (패닉 가능성 낮음)
    config = configparser.ConfigParser()
    config.read(config_path)
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
    redis_client = None
    server = None
    shutdown_event = asyncio.Event()
    
    # SIGTERM 핸들러 설정
    def handle_sigterm(signum, frame):
        logger.warning(f"Received signal {signum}. Setting shutdown event.")
        shutdown_event.set()
    
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    # 1. Redis 연결
    try:
        redis_client = await connect_to_redis(config)
    except redis.ConnectionError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return
    except redis.TimeoutError as e:
        logger.error(f"Redis connection timeout: {e}")
        return
    except Exception as e:
        logger.error(f"Unexpected error during Redis connection: {e}")
        logger.exception(e)
        return
    
    # 2. 워커 프로세스 시작
    try:
        max_workers = int(config.get('STABLEDIFFUSION', 'MAX_WORKER', fallback=1))
        workers_started = await lifecycle_manager.start_workers(
            create_worker_fn=create_worker_subprocess,
            worker_count=max_workers,
            config_path=config_path,
            worker_type='StableDiffusion'
        )
        
        if not workers_started:
            raise RuntimeError("Failed to start worker processes.")
            
    except RuntimeError as e:
        logger.error(f"Worker startup failed: {e}")
        await cleanup_redis(redis_client)
        return
    except Exception as e:
        logger.error(f"Unexpected error during worker startup: {e}")
        logger.exception(e)
        await cleanup_redis(redis_client)
        return
    
    # 3. Watchdog 프로세스 시작
    try:
        lifecycle_manager.start_watchdog(create_watchdog_subprocess)
        logger.info("Watchdog process started successfully.")
    except Exception as e:
        logger.error(f"Failed to start watchdog process: {e}")
        logger.exception(e)
        await cleanup_partial(redis_client, None, lifecycle_manager)
        return
    
    # 4. gRPC 서버 시작 및 실행
    try:
        server = await setup_grpc_server(config, redis_client)
        await wait_for_shutdown(server, shutdown_event)
        
    except grpc.RpcError as e:
        logger.error(f"gRPC server error: {e}")
        logger.exception(e)
    except OSError as e:
        logger.error(f"Failed to bind gRPC server port: {e}")
        logger.exception(e)
    except KeyboardInterrupt:
        logger.warning("Server stopping due to KeyboardInterrupt.")
    except Exception as e:
        logger.critical(f"Unexpected error during server operation: {e}")
        logger.exception(e)
    finally:
        await cleanup_all(server, redis_client, lifecycle_manager)


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