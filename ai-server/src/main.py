import grpc.aio as grpc
import asyncio
import redis.asyncio as redis
import configparser
import time
import os
import signal
import argparse
from loguru import logger

from interface import diffusion_processing_pb2_grpc
from interface.diffusion_service import DiffusionProcessingServicer, create_worker_subprocess
from utility.logger import setup_logger


async def wait_for_workers_with_backoff(worker_processes, max_retries=10, initial_delay=0.1, max_delay=5.0):
    """
    워커 프로세스들이 모두 살아있을 때까지 exponential backoff로 대기
    """
    delay = initial_delay
    
    for attempt in range(max_retries):
        all_alive = True
        dead_workers = []
        
        for p in worker_processes:
            if not p.is_alive():
                all_alive = False
                dead_workers.append(p.pid)
        
        if all_alive:
            logger.success(f"All {len(worker_processes)} worker processes are alive after {attempt + 1} attempts.")
            return True
        
        if attempt < max_retries - 1:
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries}: {len(dead_workers)} worker(s) not yet alive. "
                f"PIDs: {dead_workers}. Retrying in {delay:.2f} seconds..."
            )
            await asyncio.sleep(delay)
            
            # Exponential backoff with cap
            delay = min(delay * 2, max_delay)
        else:
            logger.error(
                f"Failed to start all workers after {max_retries} attempts. "
                f"Dead worker PIDs: {dead_workers}"
            )
    
    return False


async def run_server(config_path: str):
    """서버 설정 및 실행 (loguru 실행)"""
    config = configparser.ConfigParser()
    config.read(config_path)

    # --- 1. 로거 설정 ---
    setup_logger(config_path)

    # --- 2. 프로세스 시작 및 gRPC 서버 실행 ---
    worker_processes = []
    server = None
    try:
        logger.info("="*10 + " gRPC Server Starting " + "="*10)
        
        # Redis 연결
        redis_use_uds = config.getboolean('REDIS', 'USE_UDS')
        redis_db = int(config['REDIS']['DB'])

        if redis_use_uds:
            # UDS를 사용할 때
            redis_uds_path = config.get('REDIS', 'UDS_PATH')
            logger.info(f"Connecting to Redis UDS at {redis_uds_path}")
            redis_client = redis.Redis(unix_socket_path=redis_uds_path, db=redis_db)
        else:
            # TCP를 사용할 때
            redis_host = config.get('REDIS', 'HOST')
            redis_port = int(config.get('REDIS', 'PORT'))
            redis_timeout = int(config.get('REDIS', 'REDIS_TIMEOUT'))
            logger.info(f"Connecting to Redis at {redis_host}:{redis_port}")
            redis_client = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                db=redis_db, 
                decode_responses=False,
                socket_connect_timeout=redis_timeout,
            )
        
        await redis_client.ping()
        logger.success("Successfully connected to Redis.")

        # 서브 프로세스 시작
        max_workers = int(config.get('STABLEDIFFUSION', 'MAX_WORKER', fallback=1))

        for i in range(max_workers):
            process_name = f'LLE_worker_{i}'
            worker_process = create_worker_subprocess(
                config_path=config_path,
                worker_type='StableDiffusion',
                process_name=process_name,
            )
            worker_process.start()
            worker_processes.append(worker_process)
            logger.info(f"WORKER(PID {worker_process.pid}) - Worker process starting.")

        # 워커 프로세스들이 모두 시작될 때까지 exponential backoff로 대기
        workers_ready = await wait_for_workers_with_backoff(
            worker_processes,
            max_retries=10,
            initial_delay=0.1,
            max_delay=5.0
        )
        
        if not workers_ready:
            # 일부 워커가 시작되지 않은 경우 처리
            alive_workers = [p for p in worker_processes if p.is_alive()]
            dead_workers = [p for p in worker_processes if not p.is_alive()]
            
            logger.error(
                f"Failed to start all worker processes. "
                f"Alive: {len(alive_workers)}, Dead: {len(dead_workers)}"
            )
            
            # 살아있는 워커들 정리
            for p in alive_workers:
                logger.info(f"Terminating alive worker (PID: {p.pid})")
                os.kill(p.pid, signal.SIGINT)
                p.join(timeout=5)
                if p.is_alive():
                    p.terminate()
            
            raise SystemExit("Failed to start all worker processes.")

        # gRPC 서버 설정
        grpc_port = int(config['GRPC']['PORT'])
        message_length = int(config['GRPC']['MAX_MESSAGE_LENGTH'])
        options = [
            ('grpc.max_send_message_length', message_length),
            ('grpc.max_receive_message_length', message_length),
        ]
        
        # gRPC 서버 시작
        server = grpc.server(options=options)
        
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
        await server.wait_for_termination()

    except KeyboardInterrupt:
        logger.warning("Server stopping due to KeyboardInterrupt.")
    except Exception as e:
        logger.critical(f"A critical error occurred: {e}")
        logger.exception(e)
    finally:
        logger.info("Initiating shutdown sequence.")
        
        # gRPC 서버 종료
        if server:
            await server.stop(grace=1)
            logger.info("gRPC server stopped.")
        
        # 워커 프로세스 종료
        if worker_processes:
            logger.info("Terminating worker processes...")
            
            # SIGTERM 먼저 보내어 graceful shutdown 시도
            for p in worker_processes:
                if p.is_alive():
                    logger.debug(f"Sending SIGTERM to worker (PID: {p.pid})")
                    p.terminate()
            
            # 워커가 종료될 때까지 대기 (최대 10초)
            start_time = asyncio.get_event_loop().time()
            while any(p.is_alive() for p in worker_processes):
                if asyncio.get_event_loop().time() - start_time > 10:
                    break
                await asyncio.sleep(0.1)
            
            # 아직 살아있는 워커가 있으면 강제 종료
            for p in worker_processes:
                if p.is_alive():
                    logger.warning(f"Worker process (PID: {p.pid}) did not terminate gracefully. Forcing kill...")
                    p.kill()
                    p.join(timeout=1)
                    
            logger.info("All worker processes terminated.")
        
        # 이벤트 루프 정리 전 약간의 지연
        await asyncio.sleep(0.5)
        logger.success("Shutdown complete.")


if __name__ == '__main__':
    import multiprocessing
    try:
        multiprocessing.set_start_method('spawn', force=True)
        # print("Successfully set multiprocessing start method to 'spawn'.")
    except RuntimeError:
        print("Multiprocessing start method already set or 'spawn' not available with force=True.")

    parser = argparse.ArgumentParser(description='Image Processing Server')
    parser.add_argument('--config', type=str, default='./ai_server_config.ini', help='Path to the configuration file')
    args = parser.parse_args()

    try:
        asyncio.run(run_server(args.config))
    except KeyboardInterrupt:
        logger.info("Server process interrupted by user.")