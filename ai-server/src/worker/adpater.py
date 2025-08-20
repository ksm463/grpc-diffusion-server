import asyncio
import msgpack
import redis
import os
import configparser
import traceback
import time
import signal
from typing import Optional, Dict, Any
from loguru import logger


# logger 가져오기
try:
    from utility.logger import setup_logger
except ImportError:
    import sys
    current_file_path = os.path.abspath(__file__)
    # adapter.py의 위치에 따라 경로를 조정해야 합니다.
    # 예: /grpc-ai-server/src/worker/adapter.py -> /grpc-ai-server/src
    src_dir = os.path.dirname(os.path.dirname(current_file_path))
    if src_dir not in sys.path:
        sys.path.append(src_dir)
    from utility.logger import setup_logger

# --- 변경: sd_worker 임포트 ---
try:
    from worker.sd_worker import StableDiffusionWorker
except ImportError:
    from sd_worker import StableDiffusionWorker

from utility import convert_dtype_from_string

try:
    import cupy as cp
except ImportError:
    # cupy가 설치되지 않았을 경우 none으로 처리하고 메시지 출력. 바로 워커가 중단되지는 않는다.
    cp = None
    print("Warning: cupy not found. Ensure it's available for sd_worker")


class RedisSDAdapter:
    def __init__(self,
                sd_worker_params: Dict[str, Any],
                redis_connection_params: Dict[str, Any],
                redis_result_prefix: str,
                redis_result_channel_prefix: str, 
                redis_ttl: int,
                logger_instance: Optional[Any] = None):

        self.redis_queue_key = sd_worker_params['queue_key']
        self.redis_result_prefix = redis_result_prefix
        self.redis_result_channel_prefix = redis_result_channel_prefix
        self.redis_ttl = redis_ttl

        self.logger = logger_instance or logger
        
        # Create Redis client internally using connection parameters
        try:
            if redis_connection_params['use_uds']:
                self.redis_client = redis.Redis(
                    unix_socket_path = redis_connection_params['uds_path'],
                    db = redis_connection_params['db'],
                    decode_responses=False,
                )
            else:
                self.redis_client = redis.Redis(
                    host = redis_connection_params['host'],
                    port = redis_connection_params['port'],
                    db = redis_connection_params['db'],
                    decode_responses=False,
                )
            self.redis_client.ping()
            self.logger.info(f"Successfully connected to Redis at {redis_connection_params.get('host', 'unknown_host')}:{redis_connection_params.get('port', 'unknown_port')}")
        except redis.exceptions.ConnectionError as e:
            self.logger.error(f"Failed to connect to Redis with params {redis_connection_params}: {e}\n{traceback.format_exc()}")
            raise  # Re-raise the exception to signal initialization failure
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during Redis client initialization: {e}\n{traceback.format_exc()}")
            raise

        self.sd_worker = StableDiffusionWorker(
            model_path=sd_worker_params['model_path'],
            batch_size=sd_worker_params.get('batch_size', 1),
            queue_length=sd_worker_params.get('queue_length', 200),
            device_id=sd_worker_params.get('device_id', 0),
            logger=sd_worker_params.get('logger', self.logger)
        )

        self._running = False
        self._tasks = []
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    async def _input_to_redis_loop(self):
        self.logger.info("Redis-to-Input loop started.")
        while self._running:
            job_uuid = None
            try:
                # Blocking call, run in executor. Timeout allows checking self._running.
                task_data_bytes = await self.loop.run_in_executor(None, lambda: self.redis_client.brpop(self.redis_queue_key, timeout=1))
                if not self._running or not task_data_bytes:
                    continue

                queue_name, job_id_bytes = task_data_bytes
                job_id = job_id_bytes.decode('utf-8')

                # job_id로 실제 작업 데이터를 가져옴
                packed_job_data = await self.loop.run_in_executor(
                    None, lambda: self.redis_client.get(f"job:{job_id}")
                )
                if not packed_job_data:
                    self.logger.warning(f"Job ID '{job_id}' received, but no job data found.")
                    continue

                job_data_dict = msgpack.unpackb(packed_job_data, raw=False)
                
                # job_id 키 확인
                job_uuid = job_data_dict.get('job_id', 'unknown_uuid')
                short_uuid = job_uuid[:8]
                self.logger.debug(f"Received job from Redis: {short_uuid}")

                worker_input_item = job_data_dict.copy()
                worker_input_item['timings'] = {
                    'adapter_enqueue_time': time.perf_counter()
                }

                await self.sd_worker.input_queue.put(worker_input_item)
                self.logger.debug(f"Put item {short_uuid} into SD worker input queue.")
                
            except Exception as e:
                self.logger.error(f"Error in Redis-to-Input loop (UUID: {job_uuid}): {e}\n{traceback.format_exc()}")
                if not self._running:
                    break
                await asyncio.sleep(0.01)
        self.logger.info("Redis-to-Input loop finished.")

    async def _output_to_redis_loop(self):
        self.logger.info("Redis-to-Output loop started.")
        while self._running or not self.sd_worker.output_queue.empty():
            output_data_dict = None
            try:
                output_data_dict = await asyncio.wait_for(
                    self.sd_worker.output_queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                if not self._running and self.sd_worker.output_queue.empty(): 
                    break
                continue
            except asyncio.CancelledError:
                self.logger.info("Output-to-Redis loop cancelled.")
                break
            except Exception as e:
                self.logger.error(f"Error getting from SD output queue: {e}\n{traceback.format_exc()}")
                if not self._running: 
                    break
                await asyncio.sleep(0.01)
                continue
            
            job_uuid = output_data_dict.get('job_id')
            if not job_uuid:
                self.logger.warning(f"Job received from worker has no UUID. Skipping. Data: {output_data_dict}")
                continue
            short_uuid = job_uuid[:8]
            
            try:
                result_data_to_pack = {
                    'image_data': output_data_dict.get('image_data'),
                    'used_seed': output_data_dict.get('used_seed'),
                }

                # 1. msgpack으로 직렬화
                packed_result = msgpack.packb(result_data_to_pack, use_bin_type=True)
                
                # 2. 결과 저장
                result_key = f"{self.redis_result_prefix}{job_uuid}"
                await self.loop.run_in_executor(
                    None,
                    lambda: self.redis_client.set(result_key, packed_result, ex=self.redis_ttl)
                )
                
                # 3. 완료 신호 전송 ('SUCCESS' 메시지)
                result_channel = f"{self.redis_result_channel_prefix}{job_uuid}"
                await self.loop.run_in_executor(
                    None,
                    lambda: self.redis_client.publish(result_channel, 'SUCCESS')
                )
                self.logger.debug(f"[{short_uuid}] Published completion notification to channel '{result_channel}'")
                
                self.sd_worker.output_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error in Output-to-Redis processing (UUID: {job_uuid}): {e}\n{traceback.format_exc()}")
        self.logger.info("Output-to-Redis loop finished.")

    # redis 비동기 루프 실행
    async def start(self):
        if self._running:
            self.logger.warning("Adapter already running.")
            return

        self._running = True
        # 현재 실행중인 이벤트 루프를 self.loop에 할당
        self.loop = asyncio.get_running_loop()

        self.logger.info("Starting SD worker...")
        worker_main_task = self.loop.create_task(self.sd_worker.start(), name="SDWorkerInternal")
        self._tasks.append(worker_main_task)
        
        await asyncio.sleep(0.5) 
        if not self.sd_worker.asyncio_event.is_set():
             self.logger.warning("SD worker asyncio_event not set after start. Check SD worker logs.")

        redis_to_input_task = self.loop.create_task(self._input_to_redis_loop(), name="RedisToInput")
        output_to_redis_task = self.loop.create_task(self._output_to_redis_loop(), name="OutputToRedis")
        self._tasks.extend([redis_to_input_task, output_to_redis_task])
        self.logger.info("RedisSDAdapter started with all tasks.")

    # 비동기 태스크 취소
    async def stop(self):
        if not self._running:
            self.logger.warning("Adapter not running or already stopped.")
            return

        self.logger.info("Stopping RedisSDAdapter...")
        self._running = False 

        # sd_worker에게 종료 신호 보내기 (내부 태스크들이 스스로 종료되도록)
        if self.sd_worker and self.sd_worker.asyncio_event.is_set():
            self.logger.info("Requesting SD worker shutdown...")
            self.sd_worker.asyncio_event.clear()

        # 어댑터의 모든 태스크(sd_worker 포함)에 취소 요청 보내기
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # 모든 태스크가 취소 완료될 때까지 기다리기
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self.logger.info("All adapter tasks finished gathering.")
        
        self._tasks = []
        self.logger.info("RedisSDAdapter stopped.")

    # stop 호출 전까지 작업 실행
    async def run_forever(self):
        try:
            await self.start()
            # Wait for the main operational tasks to complete or be cancelled
            operational_tasks = [t for t in self._tasks if not t.done()]
            if operational_tasks:
                await asyncio.gather(*operational_tasks, return_exceptions=True)
        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt received. Stopping adapter...")
        except Exception as e:
            self.logger.error(f"Unhandled exception in run_forever: {e}\n{traceback.format_exc()}")
        finally:
            # Ensure stop is called even if start didn't fully complete or run_forever was interrupted early
            if self._running or any(not t.done() for t in self._tasks):
                 await self.stop()
    

    @classmethod
    def run_adapter_in_subprocess(
        cls,
        config_path,
        worker_type = 'LowLightEnhance',
    ):
        """
        서브프로세스에서 RedisSDAdapter를 실행하기 위한 클래스 메서드.
        이 함수는 multiprocessing.Process의 target으로 사용됩니다.
        """
        setup_logger(config_path)
        logger.info(f"Adapter subprocess target function started (PID: {os.getpid()}).")

        # --- [시작] 신호 처리를 위한 로직 추가 ---
        adapter_instance = None
        loop = asyncio.get_event_loop()

        def _signal_handler():
            """Graceful shutdown을 위한 신호 핸들러"""
            logger.warning("Shutdown signal received. Initiating graceful shutdown...")
            if adapter_instance:
                # adapter.stop() 코루틴을 이벤트 루프에서 실행 예약
                asyncio.ensure_future(adapter_instance.stop(), loop=loop)

        # SIGINT (Ctrl+C)와 SIGTERM에 대한 핸들러 등록
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)
        # --- [종료] 신호 처리를 위한 로직 추가 ---
        
        config = configparser.ConfigParser()
        config.read(config_path)
        
        worker_section = worker_type.upper()

        sd_worker_params = dict(
            model_path = config[worker_section]['MODEL_PATH'],
            batch_size = int(config[worker_section]['BATCH_SIZE']),
            queue_length = int(config[worker_section]['QUEUE_LENGTH']),
            device_id = int(config[worker_section]['DEVICE_ID']),
            queue_key = config[worker_section]['QUEUE_KEY']
        )
        redis_result_prefix = config[worker_section]['RESULT_KEY_PREFIX']

        redis_connection_params = dict(
            host = config['REDIS']['HOST'],
            port = int(config['REDIS']['PORT']),
            db = int(config['REDIS']['DB']),
            use_uds = config.getboolean('REDIS', 'USE_UDS'),
            uds_path = config['REDIS']['UDS_PATH']
        )

        result_channel_prefix = config.get(worker_section, 'RESULT_CHANNEL_PREFIX', fallback='result:channel:')
        redis_ttl = int(config['REDIS']['OUTPUT_TTL'])


        try:
            adapter = cls( # Use cls to instantiate
                sd_worker_params=sd_worker_params,
                redis_connection_params=redis_connection_params,
                redis_result_prefix=redis_result_prefix,
                redis_result_channel_prefix=result_channel_prefix,
                redis_ttl=redis_ttl,
                logger_instance=logger
            )
            asyncio.run(adapter.run_forever())
        except Exception as e:
            logger.error(f"Error in adapter subprocess execution: {e}\n{traceback.format_exc()}")
        finally:
            logger.info(f"Adapter subprocess target function finished (PID: {os.getpid()}).")


if __name__ == "__main__":
    pass
