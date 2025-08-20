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
        redis_uds_path = config.get('REDIS', 'UDS_PATH')
        redis_host = config['REDIS']['HOST']
        redis_port = int(config['REDIS']['PORT'])
        redis_db = int(config['REDIS']['DB'])

        if redis_use_uds:
            redis_uds_path = config['REDIS']['UDS_PATH']
            logger.info(f"Connecting to Redis UDS at {redis_uds_path}")
            redis_client = redis.Redis(unix_socket_path=redis_uds_path, db=redis_db)
        else:
            logger.info(f"Connecting to Redis at {redis_host}:{redis_port}")
            redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=False)
        
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

        # <--- 2. time.sleep()을 asyncio.sleep()으로 변경
        await asyncio.sleep(1) 

        # 모든 워커가 살아있는지 확인
        for p in worker_processes:
            if not p.is_alive():
                logger.error(f"WORKER(PID {p.pid}) - Worker process failed to start.")
                raise SystemExit("Worker process failed to start.")
        logger.success(f"All {len(worker_processes)} worker processes are alive.")

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
        processing_timeout = int(config.get('STABLEDIFFUSION', 'TIMEOUT'))

        servicer = DiffusionProcessingServicer(
            redis_client=redis_client,
            queue_key=queue_key,
            result_key_prefix=result_key_prefix,
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
        if server:
            await server.stop(grace=1)
            logger.info("gRPC server stopped.")
        if worker_processes:
            logger.info("Terminating worker processes...")
            for p in worker_processes:
                if p.is_alive():
                    os.kill(p.pid, signal.SIGINT)
            
            # 모든 프로세스가 종료될 때까지 잠시 대기
            for p in worker_processes:
                p.join(timeout=10)
                if p.is_alive():
                    logger.warning(f"Worker process (PID: {p.pid}) did not terminate gracefully. Forcing termination...")
                    p.terminate()
            logger.info("All worker processes terminated.")
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
