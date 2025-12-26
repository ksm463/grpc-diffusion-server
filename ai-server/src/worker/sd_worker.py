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
        self.logger.info(f"Loading model from {self.model_path}")
        self.device = f"cuda:{self.device_id}"
        
        self.pipe = DiffusionPipeline.from_pretrained(
            self.model_path,
            torch_dtype=torch.float32,
            use_safetensors=True,
            device_map="balanced"
        )

        self.logger.info("Model loaded and distributed across GPUs successfully.")

        self._init_queue()
        self._init_async_components()
        self.tasks = []
        self._shutdown_in_progress = False
        self._executor = None  # 추론용 executor 저장

    def _init_queue(self):
        self.input_queue = asyncio.Queue(self.queue_length)
        self.inference_input_queue = asyncio.Queue(self.queue_length)
        self.postprocessing_input_queue = asyncio.Queue(self.queue_length)
        self.output_queue = asyncio.Queue(self.queue_length)

    def _init_async_components(self):
        self.asyncio_event = asyncio.Event()
        self.asyncio_event.set()

    async def preprocessing(self):
        # 1. 전처리: 요청 데이터를 모델 추론에 필요한 형태로 가공
        try:
            while self.asyncio_event.is_set():
                try:
                    item = await asyncio.wait_for(
                        self.input_queue.get(), timeout=self.QUEUE_GET_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    self.logger.debug("Preprocessing task cancelled.")
                    break

                try:
                    # 추론에 사용할 파라미터를 준비
                    prompt = item.get('prompt')
                    height = item.get('height', 512)
                    width = item.get('width', 512)
                    num_inference_steps = item.get('num_inference_steps', 28)
                    guidance_scale = item.get('guidance_scale', 7.0)
                    seed = item.get('seed')

                    # PyTorch Generator 객체 생성
                    generator = torch.Generator(device=self.device)
                    if seed is not None and seed > 0:
                        generator.manual_seed(seed)
                    
                    # 가공된 파라미터를 item 딕셔너리에 추가
                    item['inference_params'] = {
                        'prompt': prompt,
                        'height': height,
                        'width': width,
                        'num_inference_steps': num_inference_steps,
                        'guidance_scale': guidance_scale,
                        'generator': generator
                    }

                    await self.inference_input_queue.put(item)
                    
                except Exception as e:
                    self.logger.error(f"Error processing item in preprocessing: {e}")
                    error_output = item.copy()
                    error_output['status'] = 'error'
                    error_output['error_message'] = f"Preprocessing error: {str(e)}"
                    await self.output_queue.put(error_output)

        except asyncio.CancelledError:
            self.logger.info("Preprocessing task cancelled during shutdown.")
            raise
        except Exception as e:
            self.logger.error(f"Fatal error in preprocessing: {e}\n{traceback.format_exc()}")
        finally:
            self.logger.debug("Preprocessing task exiting.")

    async def inference(self):
        # 2. 추론: 파라미터를 사용하여 모델 실행
        loop = asyncio.get_running_loop()
        
        # 전용 executor 생성 (graceful shutdown을 위해)
        from concurrent.futures import ThreadPoolExecutor
        self._executor = ThreadPoolExecutor(max_workers=1)
        
        try:
            while self.asyncio_event.is_set():
                try:
                    item = await asyncio.wait_for(
                        self.inference_input_queue.get(), timeout=self.QUEUE_GET_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    self.logger.debug("Inference task cancelled.")
                    break

                try:
                    self.logger.info(f"Starting inference for prompt: '{item['prompt']}'")
                    start_time = time.perf_counter()
                    
                    # Preprocessing 단계에서 준비된 파라미터를 가져옴
                    inference_params = item['inference_params']
                    used_seed = inference_params['generator'].seed()

                    # Executor를 사용하여 추론 실행
                    result_images = await loop.run_in_executor(
                        self._executor, 
                        lambda: self.pipe(**inference_params).images
                    )
                    
                    inference_time = time.perf_counter() - start_time
                    self.logger.info(f"Inference finished in {inference_time:.2f} seconds. Seed: {used_seed}")

                    output_data = item.copy()
                    del output_data['inference_params']  # 추후 단계에 불필요하므로 삭제
                    output_data['images'] = result_images
                    output_data['used_seed'] = used_seed
                    output_data['timings'] = item.get('timings', {})
                    output_data['timings']['inference_time'] = inference_time
                    output_data['status'] = 'success'
                    
                    await self.postprocessing_input_queue.put(output_data)
                    
                except Exception as e:
                    self.logger.error(f"Error processing item in inference: {e}")
                    error_output = item.copy()
                    error_output['status'] = 'error'
                    error_output['error_message'] = f"Inference error: {str(e)}"
                    await self.output_queue.put(error_output)

        except asyncio.CancelledError:
            self.logger.info("Inference task cancelled during shutdown.")
            raise
        except Exception as e:
            self.logger.error(f"Fatal error in inference: {e}\n{traceback.format_exc()}")
        finally:
            # Executor 정리
            if self._executor:
                self._executor.shutdown(wait=False)
            self.logger.debug("Inference task exiting.")

    async def postprocessing(self):
        # 3. 후처리: 텐서 역정규화 -> PIL Image를 Bytes로 변환
        try:
            while self.asyncio_event.is_set():
                try:
                    item = await asyncio.wait_for(
                        self.postprocessing_input_queue.get(), timeout=self.QUEUE_GET_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    self.logger.debug("Postprocessing task cancelled.")
                    break
                
                try:
                    prompt_preview = item.get('prompt', 'N/A')[:50] + '...'
                    self.logger.info(f"Postprocessing started for prompt: '{prompt_preview}'")
                    
                    start_time = time.perf_counter()
                    
                    image = item['images'][0]
                    byte_arr = io.BytesIO()
                    # 이미지가 RGBA 형태인 경우 RGB형태로 변환
                    if image.mode == 'RGBA':
                        self.logger.info("Image is in RGBA mode, converting to RGB for JPEG format.")
                        image = image.convert('RGB')
                    image.save(byte_arr, format='JPEG')
                    image_bytes = byte_arr.getvalue()

                    postprocessing_time = time.perf_counter() - start_time

                    output_data = item.copy()
                    del output_data['images']
                    output_data['image_data'] = image_bytes
                    output_data['timings']['postprocessing_time'] = postprocessing_time

                    await self.output_queue.put(output_data)
                    
                    self.logger.info(f"Postprocessing finished in {postprocessing_time:.4f} seconds. Item moved to output_queue.")
                    
                except Exception as e:
                    self.logger.error(f"Error processing item in postprocessing: {e}")
                    error_output = item.copy()
                    error_output['status'] = 'error'
                    error_output['error_message'] = f"Postprocessing error: {str(e)}"
                    await self.output_queue.put(error_output)

        except asyncio.CancelledError:
            self.logger.info("Postprocessing task cancelled during shutdown.")
            raise
        except Exception as e:
            self.logger.error(f"Fatal error in postprocessing: {e}\n{traceback.format_exc()}")
        finally:
            self.logger.debug("Postprocessing task exiting.")

    async def start(self):
        """Starts the worker tasks concurrently."""
        if not self.logger:
            print("Warning: Logger not provided.")
            import logging
            self.logger = logging.getLogger("sd_worker")
            if not self.logger.hasHandlers():
                logging.basicConfig(level=logging.INFO)

        self.logger.info(f"Starting sd_worker on device {self.device_id}...")
        self.asyncio_event.set()

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # adapter가 asyncio_event.clear()를 호출하여 종료 신호를 보냄

        self.tasks = [
            asyncio.create_task(self.preprocessing(), name="Preprocessing"),
            asyncio.create_task(self.inference(), name="Inference"),
            asyncio.create_task(self.postprocessing(), name="Postprocessing")
        ]

        try:
            await asyncio.gather(*self.tasks, return_exceptions=False)
        except asyncio.CancelledError:
            self.logger.info("Worker tasks cancelled.")
        except Exception as e:
            self.logger.error(f"Error in worker tasks: {e}")
        finally:
            self.logger.info("All worker tasks finished.")

    async def stop(self):
        """Gracefully stop the worker."""
        if self._shutdown_in_progress:
            return
        
        self._shutdown_in_progress = True
        self.logger.info("Initiating graceful shutdown of SD worker...")
        
        # 이벤트를 clear하여 모든 루프 종료
        self.asyncio_event.clear()
        
        # 작업 완료 대기
        await asyncio.sleep(0.1)
        
        # 모든 태스크 취소
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # 태스크 타임아웃 설정
        if self.tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.tasks, return_exceptions=True),
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("Some worker tasks did not finish within timeout.")
            except Exception as e:
                self.logger.error(f"Error during task cleanup: {e}")
        
        # Executor 정리
        if self._executor:
            self._executor.shutdown(wait=False)
        
        # 큐 정리 - 남아있는 아이템들을 비움
        for queue in [self.input_queue, self.inference_input_queue, 
                     self.postprocessing_input_queue, self.output_queue]:
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        
        self.logger.info("SD worker shutdown complete.")

    def _signal_handler(self):
        """Handles shutdown signals - Deprecated, handled by adapter now."""
        self.logger.warning("Direct signal handler called - this should be handled by adapter.")
        # 직접 sys.exit()를 호출하지 않고 adapter가 처리하도록 함