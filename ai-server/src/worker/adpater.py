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


try:
    from utility.logger import setup_logger
except ImportError:
    import sys
    current_file_path = os.path.abspath(__file__)
    src_dir = os.path.dirname(os.path.dirname(current_file_path))
    if src_dir not in sys.path:
        sys.path.append(src_dir)
    from utility.logger import setup_logger

try:
    from worker.sd_worker import StableDiffusionWorker
except ImportError:
    from sd_worker import StableDiffusionWorker

try:
    import cupy as cp
except ImportError:
    cp = None
    print("Warning: cupy not found. Ensure it's available for sd_worker")


class RedisSDAdapter:
    """
    Redis를 통해 작업을 수신하고 StableDiffusionWorker에게 전달.
    생성이 완료되면 다시 Redis로 전송하는 어댑터 클래스
    """
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
        
        # Redis 클라이언트 연결
        self.redis_client = self._initialize_redis_client(redis_connection_params)

        self.sd_worker = StableDiffusionWorker(
            model_path=sd_worker_params['model_path'],
            queue_length=sd_worker_params.get('queue_length', 200),
            device_id=sd_worker_params.get('device_id', 0),
            logger=sd_worker_params.get('logger', self.logger)
        )

        self._is_running = False
        self._tasks = []
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
    def _initialize_redis_client(self, params: Dict[str, Any]) -> redis.Redis:
        """Redis 클라이언트를 생성하고 연결을 확인"""
        try:
            if params['use_uds']:
                client = redis.Redis(
                    unix_socket_path=params['uds_path'],
                    db=params['db'],
                    decode_responses=False,
                )
                connection_info = f"UDS at {params['uds_path']}"
            else:
                client = redis.Redis(
                    host=params['host'],
                    port=params['port'],
                    db=params['db'],
                    decode_responses=False,
                    socket_connect_timeout=params.get('timeout', 5)
                )
                connection_info = f"{params.get('host', 'unknown')}:{params.get('port', 'unknown')}"
                
            client.ping()
            self.logger.info(f"Successfully connected to Redis via {connection_info}")
            return client
        except redis.exceptions.ConnectionError as e:
            self.logger.error(f"Failed to connect to Redis with params {params}: {e}\n{traceback.format_exc()}")
            raise
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during Redis client initialization: {e}\n{traceback.format_exc()}")
            raise

    async def _fetch_jobs_from_redis(self):
        """Redis 큐에서 작업을 가져와 워커의 입력 큐로 전달"""
        self.logger.info("Redis-to-Worker loop started.")
        while self._is_running:
            job_uuid = None
            try:
                # 블로킹 호출(brpop)을 비동기적으로 실행
                task_data_bytes = await self.loop.run_in_executor(
                    None, lambda: self.redis_client.brpop(self.redis_queue_key, timeout=1)
                )
                if not self._is_running or not task_data_bytes:
                    continue

                _, job_id_bytes = task_data_bytes
                job_id = job_id_bytes.decode('utf-8')

                # job_id로 실제 작업 데이터 조회
                packed_job_data = await self.loop.run_in_executor(
                    None, lambda: self.redis_client.get(f"job:{job_id}")
                )
                if not packed_job_data:
                    self.logger.warning(f"Job ID '{job_id}' received, but no job data found.")
                    continue

                job_data_dict = msgpack.unpackb(packed_job_data, raw=False)
                
                job_uuid = job_data_dict.get('job_id', 'unknown_uuid')
                short_uuid = job_uuid[:8]
                self.logger.debug(f"Received job from Redis: {short_uuid}")

                worker_input_item = job_data_dict.copy()
                worker_input_item['timings'] = { 'adapter_enqueue_time': time.perf_counter() }

                await self.sd_worker.input_queue.put(worker_input_item)
                self.logger.debug(f"Put item {short_uuid} into SD worker input queue.")
                
            except KeyError as e:
                error_message = f"Missing required field in job data: {e}"
                self.logger.error(error_message)
                if job_uuid:
                    await self._publish_error_to_redis(job_uuid, error_message)
            except Exception as e:
                self.logger.error(f"Error in Redis-to-Worker loop (UUID: {job_uuid}): {e}\n{traceback.format_exc()}")
                if not self._is_running:
                    break
                await asyncio.sleep(0.01)
        self.logger.info("Redis-to-Worker loop finished.")

    async def _publish_results_to_redis(self):
        """워커의 출력 큐에서 결과를 가져와 Redis에 게시"""
        self.logger.info("Worker-to-Redis loop started.")
        while self._is_running or not self.sd_worker.output_queue.empty():
            try:
                output_data_dict = await asyncio.wait_for(self.sd_worker.output_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                if not self._is_running and self.sd_worker.output_queue.empty():
                    break
                continue
            except asyncio.CancelledError:
                self.logger.info("Worker-to-Redis loop cancelled.")
                break
            
            job_uuid = output_data_dict.get('job_id')
            if not job_uuid:
                self.logger.warning(f"Job from worker has no UUID. Skipping. Data: {output_data_dict}")
                self.sd_worker.output_queue.task_done()
                continue
            
            short_uuid = job_uuid[:8]
            self.logger.info(f"[{short_uuid}] Got item from output_queue. Preparing to send to Redis.")
            
            try:
                status = output_data_dict.get('status', 'error')
                if status == 'success':
                    result_data_to_pack = {
                        'image_data': output_data_dict.get('image_data'),
                        'used_seed': output_data_dict.get('used_seed'),
                    }
                    packed_result = msgpack.packb(result_data_to_pack, use_bin_type=True)
                    
                    result_key = f"{self.redis_result_prefix}{job_uuid}"
                    result_channel = f"{self.redis_result_channel_prefix}{job_uuid}"
                    
                    await self.loop.run_in_executor(
                        None, lambda: self.redis_client.set(result_key, packed_result, ex=self.redis_ttl)
                    )
                    await self.loop.run_in_executor(
                        None, lambda: self.redis_client.publish(result_channel, 'SUCCESS')
                    )
                    self.logger.debug(f"[{short_uuid}] Published SUCCESS to channel '{result_channel}'")
                else:
                    error_message = output_data_dict.get('error_message', 'Unknown error in worker.')
                    self.logger.error(f"[{short_uuid}] Job failed in worker. Reporting error. Reason: {error_message}")
                    await self._publish_error_to_redis(job_uuid, error_message)
            except Exception as e:
                self.logger.error(f"Error in Worker-to-Redis processing (UUID: {job_uuid}): {e}\n{traceback.format_exc()}")
            finally:
                # 성공/실패 여부와 관계없이 task_done() 호출
                self.sd_worker.output_queue.task_done()
        self.logger.info("Worker-to-Redis loop finished.")

    async def _publish_error_to_redis(self, job_uuid: str, error_message: str):
        """작업 실패 정보를 Redis에 게시합니다."""
        try:
            result_channel = f"{self.redis_result_channel_prefix}{job_uuid}"
            result_key = f"{self.redis_result_prefix}{job_uuid}"
            short_uuid = job_uuid[:8]

            self.logger.debug(f"[{short_uuid}] Publishing ERROR to channel: {result_channel}")
            
            error_payload = msgpack.packb({'error': error_message}, use_bin_type=True)
            
            # Redis에 에러 메시지 저장 후 'ERROR' 신호 전송
            await self.loop.run_in_executor(
                None, lambda: self.redis_client.set(result_key, error_payload, ex=self.redis_ttl)
            )
            await self.loop.run_in_executor(
                None, lambda: self.redis_client.publish(result_channel, 'ERROR')
            )
        except Exception as e:
            self.logger.error(f"Failed to publish error to Redis for UUID {job_uuid}: {e}")

    async def start(self):
        if self._is_running:
            self.logger.warning("Adapter already running.")
            return

        self._is_running = True
        self.loop = asyncio.get_running_loop()

        self.logger.info("Starting SD worker...")
        worker_main_task = self.loop.create_task(self.sd_worker.start(), name="SDWorkerInternal")
        self._tasks.append(worker_main_task)
        
        await asyncio.sleep(0.5) 
        if not self.sd_worker.asyncio_event.is_set():
             self.logger.warning("SD worker asyncio_event not set after start. Check SD worker logs.")

        redis_to_input_task = self.loop.create_task(self._fetch_jobs_from_redis(), name="RedisToInput")
        output_to_redis_task = self.loop.create_task(self._publish_results_to_redis(), name="OutputToRedis")
        
        self._tasks.extend([redis_to_input_task, output_to_redis_task])
        self.logger.info("RedisSDAdapter started with all tasks.")

    async def stop(self):
        if not self._is_running:
            self.logger.warning("Adapter not running or already stopped.")
            return

        self.logger.info("Stopping RedisSDAdapter...")
        self._is_running = False 

        if self.sd_worker and self.sd_worker.asyncio_event.is_set():
            self.logger.info("Requesting SD worker shutdown...")
            self.sd_worker.asyncio_event.clear()

        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self.logger.info("All adapter tasks finished gathering.")
        
        self._tasks = []
        self.logger.info("RedisSDAdapter stopped.")

    async def run_forever(self):
        try:
            await self.start()
            operational_tasks = [t for t in self._tasks if not t.done()]
            if operational_tasks:
                await asyncio.gather(*operational_tasks, return_exceptions=True)
        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt received. Stopping adapter...")
        except Exception as e:
            self.logger.error(f"Unhandled exception in run_forever: {e}\n{traceback.format_exc()}")
        finally:
            if self._is_running or any(not t.done() for t in self._tasks):
                   await self.stop()
    
    @classmethod
    def run_adapter_in_subprocess(
        cls,
        config_path,
        worker_type='StableDiffusion',
    ):
        """
        서브프로세스에서 RedisSDAdapter를 실행하기 위한 클래스 메서드.
        """
        setup_logger(config_path)
        logger.info(f"Adapter subprocess target function started (PID: {os.getpid()}).")

        adapter_instance = None
        loop = asyncio.get_event_loop()

        def _signal_handler():
            logger.warning("Shutdown signal received. Initiating graceful shutdown...")
            if adapter_instance:
                asyncio.ensure_future(adapter_instance.stop(), loop=loop)

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)
        
        try:
            config = configparser.ConfigParser()
            config.read(config_path)
            
            worker_section = worker_type.upper()

            sd_worker_params = dict(
                model_path=config[worker_section]['MODEL_PATH'],
                queue_length=int(config[worker_section]['QUEUE_LENGTH']),
                device_id=int(config[worker_section]['DEVICE_ID']),
                queue_key=config[worker_section]['QUEUE_KEY']
            )

            use_uds = config.getboolean('REDIS', 'USE_UDS')
            redis_connection_params = {
                'db': int(config['REDIS']['DB']),
                'use_uds': use_uds
            }

            if use_uds:
                # UDS를 사용하는 경우
                redis_connection_params['uds_path'] = config['REDIS']['UDS_PATH']
            else:
                # TCP를 사용하는 경우
                redis_connection_params['host'] = config['REDIS']['HOST']
                redis_connection_params['port'] = int(config['REDIS']['PORT'])
                redis_connection_params['timeout'] = int(config.get('REDIS', 'REDIS_TIMEOUT', fallback=5))
            
            adapter_instance = cls(
                sd_worker_params=sd_worker_params,
                redis_connection_params=redis_connection_params,
                redis_result_prefix=config[worker_section]['RESULT_KEY_PREFIX'],
                redis_result_channel_prefix=config[worker_section]['RESULT_CHANNEL_PREFIX'],
                redis_ttl=int(config['REDIS']['OUTPUT_TTL']),
                logger_instance=logger
            )
            loop.run_until_complete(adapter_instance.run_forever())

        except Exception as e:
            logger.error(f"Error in adapter subprocess execution: {e}\n{traceback.format_exc()}")
        finally:
            if not loop.is_closed():
                loop.close()
            logger.info(f"Adapter subprocess target function finished (PID: {os.getpid()}).")


if __name__ == "__main__":
    pass