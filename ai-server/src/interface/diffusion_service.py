import grpc
import uuid
import redis.asyncio as redis
import msgpack
import time
import traceback
from loguru import logger
import configparser
import asyncio
import multiprocessing
from loguru import logger

import diffusion_processing_pb2
import diffusion_processing_pb2_grpc

class DiffusionProcessingServicer(diffusion_processing_pb2_grpc.ImageGeneratorServicer):
    """
    gRPC 요청을 받아 Stable Diffusion 생성 작업을 Redis 큐에 제출하고,
    작업 완료 후 결과를 클라이언트에게 반환하는 Servicer 클래스.
    """
    def __init__(
        self,
        redis_client: redis.Redis,
        queue_key: str,
        result_key_prefix: str,
        processing_timeout: int,
    ):
        self.redis_client = redis_client
        self.queue_key = queue_key
        self.result_key_prefix = result_key_prefix
        self.timeout = processing_timeout
        
        # Redis Pub/Sub 채널을 위한 접두사
        self.result_channel_prefix = "result:channel:"
        
        logger.info(f"DiffusionProcessingServicer initialized.")
        logger.info(f"Using job queue: '{self.queue_key}'")
        logger.info(f"Processing timeout set to {self.timeout} seconds.")

    async def GenerateImage(self, request: diffusion_processing_pb2.GenerationRequest, context):
        """
        이미지 생성 요청(Unary RPC)을 처리하는 메인 함수
        """
        request_id = request.request_id or str(uuid.uuid4())
        short_id = request_id[:8]
        logger.info(f"[{short_id}] Received image generation request. Prompt: '{request.prompt[:50]}...'")
        
        try:
            # 1. 워커에게 전달할 작업을 Redis 큐에 전달
            await self._submit_job_to_queue(request_id, request)

            # 2. 작업이 완료될 때까지 Redis Pub/Sub을 통해 결과 대기
            result_data = await self._wait_for_job_result(request_id)

            if not result_data:
                logger.error(f"[{short_id}] Processing timed out or failed.")
                await context.abort(grpc.StatusCode.DEADLINE_EXCEEDED, "Image generation timed out or failed.")
                return

            # 3. 성공적으로 받은 결과를 gRPC 응답 메시지로 만들어 반환
            logger.success(f"[{short_id}] Successfully generated image with seed: {result_data.get('used_seed')}")
            return diffusion_processing_pb2.GenerationResponse(
                request_id=request_id,
                status=diffusion_processing_pb2.GenerationResponse.Status.SUCCESS,
                image_data=result_data.get('image_data'),
                used_seed=result_data.get('used_seed')
            )

        except redis.RedisError as e:
            logger.error(f"[{short_id}] Redis error during processing: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, "A Redis error occurred.")
        except Exception as e:
            logger.error(f"[{short_id}] An unexpected error occurred: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, "An unexpected internal error occurred.")

    async def _submit_job_to_queue(self, job_id: str, request: diffusion_processing_pb2.GenerationRequest):
        """
        gRPC 요청 데이터를 워커가 처리할 수 있는 형태로 직렬화하여 Redis 큐에 입력
        """
        short_id = job_id[:8]
        
        job_data = {
            "job_id": job_id,
            "prompt": request.prompt,
            "guidance_scale": request.guidance_scale,
            "num_inference_steps": request.num_inference_steps,
            "width": request.width,
            "height": request.height,
            "seed": request.seed,
        }

        # 데이터를 MessagePack으로 직렬화
        packed_job_data = msgpack.packb(job_data, use_bin_type=True)
        
        # Redis에 작업 데이터 저장 (워커가 job_id로 데이터를 찾을 수 있도록)
        # TTL(Time-To-Live)을 설정하여 작업이 끝나거나 실패해도 데이터가 영원히 남지 않게 함
        await self.redis_client.set(f"job:{job_id}", packed_job_data, ex=self.timeout + 60)

        # Redis 리스트(Queue)에 작업 ID를 추가
        await self.redis_client.lpush(self.queue_key, job_id)
        logger.info(f"[{short_id}] Job submitted to queue '{self.queue_key}'.")

    async def _wait_for_job_result(self, job_id: str) -> dict | None:
        """
        작업 ID의 완료 알림을 받으면 Redis에서 최종 결과물 반환
        """
        short_id = job_id[:8]
        result_channel = f"{self.result_channel_prefix}{job_id}"
        pubsub = None

        async def listen_for_message(ps: redis.client.PubSub):
            """Pub/Sub 메시지를 비동기적으로 기다리는 내부 함수"""
            async for message in ps.listen():
                if message and message.get('type') == 'message':
                    return message
        
        try:
            # 1. Pub/Sub 객체를 생성하고 작업별 고유 채널 구독
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(result_channel)
            logger.debug(f"[{short_id}] Subscribed to result channel '{result_channel}'. Waiting for completion notification...")

            # 2. 지정된 타임아웃 시간 동안 메시지 대기
            message = await asyncio.wait_for(listen_for_message(pubsub), timeout=self.timeout)
            
            if not message or message['data'].decode('utf-8') != 'SUCCESS':
                 # 워커가 실패를 알린 경우
                logger.error(f"[{short_id}] Received failure notification from worker.")
                return None

            logger.debug(f"[{short_id}] Completion notification received.")
            
            # 3. 알림을 받으면, Redis에서 최종 결과 데이터(이미지 등)를 가져옴
            result_key = f"{self.result_key_prefix}{job_id}"
            packed_result = await self.redis_client.get(result_key)
            
            if not packed_result:
                logger.error(f"[{short_id}] Notification received, but result key '{result_key}' is missing!")
                return None
            
            # 결과 데이터를 삭제하여 메모리 관리
            await self.redis_client.delete(result_key)
            
            # 4. MessagePack으로 직렬화된 결과 데이터를 파이썬 딕셔너리로 변환하여 반환
            return msgpack.unpackb(packed_result, raw=False)

        except asyncio.TimeoutError:
            logger.warning(f"[{short_id}] Timed out waiting for result from channel '{result_channel}'.")
            return None
        finally:
            # 5. 작업이 끝나면 Pub/Sub 연결 정리
            if pubsub:
                await pubsub.unsubscribe(result_channel)
                await pubsub.close()

def create_worker_subprocess(config_path: str, worker_type: str, process_name: str) -> multiprocessing.Process:
    """지정된 워커 어댑터를 별도의 서브프로세스로 실행"""
    process_args = (config_path,)
    process_kwargs = {
        'worker_type': worker_type,
        # 'logger_name': logger_name,
    }

    adapter_process = multiprocessing.Process(
        target=RedisLLEAdapter.run_adapter_in_subprocess,
        args=process_args,
        kwargs=process_kwargs,
        name=process_name,
    )
    logger.debug("worker subprocess created.")
    return adapter_process
