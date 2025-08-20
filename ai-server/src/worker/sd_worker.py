import os
import io
import asyncio
import signal
import traceback
import time
import sys
import torch
from diffusers import DiffusionPipeline
from PIL import Image

# 큐에 들어오는 데이터: {'prompt': 'a cute cat', 'timings': {}}
# 큐에서 나가는 데이터: {'prompt': '...', 'image_bytes': b'...', 'timings': {}}

class StableDiffusionWorker:
    QUEUE_GET_TIMEOUT = 0.01

    def __init__(self, model_path, batch_size=1, queue_length=20, device_id=0, logger=None):
        self.model_path = model_path
        self.batch_size = batch_size
        self.queue_length = queue_length
        self.device_id = device_id
        self.logger = logger
        self.pid = os.getpid()
        self.logger.info(f"Loading model from {self.model_path}...")
        self.device = f"cuda:{self.device_id}"
        self.pipe = DiffusionPipeline.from_pretrained(
            self.model_path,
            torch_dtype=torch.float16,
            use_safetensors=True
        )
        self.pipe.enable_model_cpu_offload() 
        self.logger.info("Model loaded successfully.")

        self._init_queue()
        self._init_async_components()
        self.tasks = []

    def _init_queue(self):
        self.input_queue = asyncio.Queue(self.queue_length)
        # 전처리 단계가 거의 필요 없으므로 큐를 단순화
        self.inference_input_queue = asyncio.Queue(self.queue_length)
        self.postprocessing_input_queue = asyncio.Queue(self.queue_length)
        self.output_queue = asyncio.Queue(self.queue_length)

    def _init_async_components(self):
        self.asyncio_event = asyncio.Event()
        self.asyncio_event.set()

    async def preprocessing(self):
        # 2. 전처리: DiffusionPipeline이 내부적으로 토크나이징, 인코딩, 노이즈 생성을 모두 처리
        # 여기서는 단순히 입력을 다음 큐로 전달하는 역할만 합니다.
        try:
            while self.asyncio_event.is_set():
                try:
                    queue_input_data = await asyncio.wait_for(
                        self.input_queue.get(), timeout=self.QUEUE_GET_TIMEOUT
                    )
                    await self.inference_input_queue.put(queue_input_data)
                except asyncio.TimeoutError:
                    continue
        except Exception as e:
            self.logger.error(f"Error in preprocessing bridge: {e}\n{traceback.format_exc()}")

    async def inference(self):
        # 3. 추론: model.predict -> pipe(...) 호출
        loop = asyncio.get_running_loop()
        try:
            while self.asyncio_event.is_set():
                try:
                    # (기존의 배치 로직은 생략하고 단순화된 버전으로 예시)
                    item = await asyncio.wait_for(
                        self.inference_input_queue.get(), timeout=self.QUEUE_GET_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    continue

                self.logger.info(f"Starting inference for prompt: '{item['prompt']}'")
                start_time = time.perf_counter()

                prompt = item.get('prompt')
                height = item.get('height', 512)
                width = item.get('width', 512)
                num_inference_steps = item.get('num_inference_steps', 28)
                guidance_scale = item.get('guidance_scale', 7.0)
                seed = item.get('seed') # None일 수 있음

                # seed가 제공되지 않으면 랜덤 시드 사용, 제공되면 해당 시드 사용
                generator = torch.Generator(device=self.device)
                if seed is not None and seed > 0:
                    generator.manual_seed(seed)
                
                # 실제 사용된 시드 값을 저장
                used_seed = generator.seed()

                result_images = await loop.run_in_executor(
                    None, 
                    lambda: self.pipe(
                        prompt=prompt,
                        height=height,
                        width=width,
                        num_inference_steps=num_inference_steps,
                        guidance_scale=guidance_scale,
                        generator=generator,
                    ).images
                )
                
                inference_time = time.perf_counter() - start_time
                self.logger.info(f"Inference finished in {inference_time:.2f} seconds. Seed: {used_seed}")

                output_data = item.copy()
                output_data['images'] = result_images
                output_data['used_seed'] = used_seed # 사용된 시드 추가
                output_data['timings'] = item.get('timings', {})
                output_data['timings']['inference_time'] = inference_time
                
                await self.postprocessing_input_queue.put(output_data)

        except Exception as e:
            self.logger.error(f"Error in inference: {e}\n{traceback.format_exc()}")

    async def postprocessing(self):
        # 4. 후처리: 텐서 역정규화 -> PIL Image를 Bytes로 변환
        try:
            while self.asyncio_event.is_set():
                try:
                    item = await asyncio.wait_for(
                        self.postprocessing_input_queue.get(), timeout=self.QUEUE_GET_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    continue
                
                start_time = time.perf_counter()

                # PIL Image를 PNG 형식의 bytes로 변환
                image = item['images'][0] # 첫 번째 이미지만 사용
                byte_arr = io.BytesIO()
                image.save(byte_arr, format='PNG')
                image_bytes = byte_arr.getvalue()
                
                postprocessing_time = time.perf_counter() - start_time

                output_data = item.copy()
                del output_data['images'] # 이미지 객체는 삭제
                output_data['image_data'] = image_bytes
                output_data['timings']['postprocessing_time'] = postprocessing_time

                await self.output_queue.put(output_data)

        except Exception as e:
            self.logger.error(f"Error in postprocessing: {e}\n{traceback.format_exc()}")

    async def start(self):
        """Starts the worker tasks concurrently."""
        if not self.logger:
            print("Warning: Logger not provided.")
            import logging
            self.logger = logging.getLogger("sd_worker")
            if not self.logger.hasHandlers(): # 핸들러 중복 추가 방지
                logging.basicConfig(level=logging.INFO)

        self.logger.info(f"Starting sd_worker_trt on device {self.device_id}...")
        self.asyncio_event.set()

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Add signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._signal_handler)

        # Create and store tasks
        self.tasks.append(asyncio.create_task(self.preprocessing(), name="Preprocessing"))
        self.tasks.append(asyncio.create_task(self.inference(), name="Inference"))
        self.tasks.append(asyncio.create_task(self.postprocessing(), name="Postprocessing"))

        # Wait for tasks to complete (e.g., if shutdown is triggered)
        await asyncio.gather(*self.tasks, return_exceptions=True)

        self.logger.info("All worker tasks finished.")

    def _signal_handler(self):
        """Handles shutdown signals."""
        if hasattr(self, '_shutdown_in_progress') and self._shutdown_in_progress:
            return
        self._shutdown_in_progress = True

        self.logger.info("Shutdown signal received. Stopping tasks...")
        self.asyncio_event.clear()
        for task in self.tasks:
            if not task.done():
                task.cancel()
        self.logger.info("Cancellation requests sent to tasks.")
        self.logger.info("Exiting worker process now.")
        sys.exit(0)
