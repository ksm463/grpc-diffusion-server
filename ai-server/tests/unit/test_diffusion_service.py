"""
Tests for interface/diffusion_service.py
"""
import pytest
import asyncio
import msgpack
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fakeredis import aioredis as fake_aioredis
import grpc

from interface.diffusion_service import (
    DiffusionProcessingServicer,
    create_worker_subprocess
)


@pytest.fixture
async def fake_redis():
    """Create fake Redis client"""
    client = fake_aioredis.FakeRedis(decode_responses=False)
    yield client
    await client.close()


@pytest.fixture
def mock_grpc_context():
    """Create mock gRPC context"""
    context = AsyncMock()
    context.abort = AsyncMock()
    return context


@pytest.fixture
def mock_generation_request():
    """Create mock GenerationRequest"""
    request = Mock()
    request.request_id = "test-request-123"
    request.prompt = "a beautiful sunset over mountains"
    request.guidance_scale = 7.5
    request.num_inference_steps = 20
    request.width = 512
    request.height = 512
    request.seed = 42
    return request


@pytest.fixture
async def servicer(fake_redis):
    """Create DiffusionProcessingServicer instance"""
    return DiffusionProcessingServicer(
        redis_client=fake_redis,
        queue_key="test_job_queue",
        result_key_prefix="result:",
        result_channel_prefix="result_channel:",
        processing_timeout=30
    )


class TestDiffusionProcessingServicer:
    """Test DiffusionProcessingServicer class"""

    def test_init_sets_attributes_correctly(self, fake_redis):
        """Should initialize servicer with correct attributes"""
        servicer = DiffusionProcessingServicer(
            redis_client=fake_redis,
            queue_key="test_queue",
            result_key_prefix="result:",
            result_channel_prefix="channel:",
            processing_timeout=60
        )

        assert servicer.redis_client == fake_redis
        assert servicer.queue_key == "test_queue"
        assert servicer.result_key_prefix == "result:"
        assert servicer.result_channel_prefix == "channel:"
        assert servicer.timeout == 60

    @pytest.mark.asyncio
    async def test_submit_job_to_queue_stores_job_data(self, servicer, fake_redis, mock_generation_request):
        """Should store job data in Redis with TTL"""
        job_id = "test-job-123"

        await servicer._submit_job_to_queue(job_id, mock_generation_request)

        # Check job data was stored
        stored_data = await fake_redis.get(f"job:{job_id}")
        assert stored_data is not None

        # Unpack and verify data
        unpacked = msgpack.unpackb(stored_data, raw=False)
        assert unpacked['job_id'] == job_id
        assert unpacked['prompt'] == mock_generation_request.prompt
        assert unpacked['guidance_scale'] == mock_generation_request.guidance_scale
        assert unpacked['num_inference_steps'] == mock_generation_request.num_inference_steps
        assert unpacked['width'] == mock_generation_request.width
        assert unpacked['height'] == mock_generation_request.height
        assert unpacked['seed'] == mock_generation_request.seed

    @pytest.mark.asyncio
    async def test_submit_job_to_queue_pushes_to_queue(self, servicer, fake_redis, mock_generation_request):
        """Should push job_id to Redis queue"""
        job_id = "test-job-456"

        await servicer._submit_job_to_queue(job_id, mock_generation_request)

        # Check job_id was pushed to queue
        queue_items = await fake_redis.lrange("test_job_queue", 0, -1)
        assert job_id.encode() in queue_items

    @pytest.mark.asyncio
    async def test_wait_for_job_result_returns_result_on_success(self, servicer, fake_redis):
        """Should return result data when success notification received"""
        job_id = "test-job-success"
        result_channel = f"result_channel:{job_id}"
        result_key = f"result:{job_id}"

        # Prepare result data
        result_data = {
            'image_data': b'fake_image_bytes',
            'used_seed': 42
        }
        packed_result = msgpack.packb(result_data, use_bin_type=True)

        # Store result in Redis
        await fake_redis.set(result_key, packed_result)

        # Simulate worker publishing success notification
        async def publish_success():
            await asyncio.sleep(0.1)
            await fake_redis.publish(result_channel, 'SUCCESS')

        # Start publish task
        publish_task = asyncio.create_task(publish_success())

        # Wait for result
        result = await servicer._wait_for_job_result(job_id)

        await publish_task

        # Verify result
        assert result is not None
        assert result['image_data'] == b'fake_image_bytes'
        assert result['used_seed'] == 42

        # Verify result key was deleted
        deleted_result = await fake_redis.get(result_key)
        assert deleted_result is None

    @pytest.mark.asyncio
    async def test_wait_for_job_result_returns_none_on_timeout(self, servicer):
        """Should return None when timeout occurs"""
        # Set very short timeout
        servicer.timeout = 0.1
        job_id = "test-job-timeout"

        # No worker will publish, so it should timeout
        result = await servicer._wait_for_job_result(job_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_wait_for_job_result_returns_none_on_failure_notification(self, servicer, fake_redis):
        """Should return None when worker sends failure notification"""
        job_id = "test-job-failure"
        result_channel = f"result_channel:{job_id}"

        # Simulate worker publishing failure notification
        async def publish_failure():
            await asyncio.sleep(0.1)
            await fake_redis.publish(result_channel, 'FAILURE')

        publish_task = asyncio.create_task(publish_failure())

        result = await servicer._wait_for_job_result(job_id)

        await publish_task

        assert result is None

    @pytest.mark.asyncio
    async def test_wait_for_job_result_returns_none_when_result_missing(self, servicer, fake_redis):
        """Should return None when result key is missing after success notification"""
        job_id = "test-job-missing-result"
        result_channel = f"result_channel:{job_id}"

        # Simulate worker publishing success but result key is missing
        async def publish_without_result():
            await asyncio.sleep(0.1)
            await fake_redis.publish(result_channel, 'SUCCESS')

        publish_task = asyncio.create_task(publish_without_result())

        result = await servicer._wait_for_job_result(job_id)

        await publish_task

        assert result is None

    @pytest.mark.asyncio
    async def test_generate_image_success_flow(self, servicer, fake_redis, mock_generation_request, mock_grpc_context):
        """Should successfully generate image and return response"""
        job_id = mock_generation_request.request_id
        result_channel = f"result_channel:{job_id}"
        result_key = f"result:{job_id}"

        # Prepare result
        result_data = {
            'image_data': b'test_image_data',
            'used_seed': 12345
        }
        packed_result = msgpack.packb(result_data, use_bin_type=True)

        # Simulate worker processing
        async def simulate_worker():
            await asyncio.sleep(0.1)
            # Worker would read job, process it, store result, and publish
            await fake_redis.set(result_key, packed_result)
            await fake_redis.publish(result_channel, 'SUCCESS')

        worker_task = asyncio.create_task(simulate_worker())

        # Call GenerateImage
        response = await servicer.GenerateImage(mock_generation_request, mock_grpc_context)

        await worker_task

        # Verify response
        assert response.request_id == job_id
        assert response.status == 0  # SUCCESS status
        assert response.image_data == b'test_image_data'
        assert response.used_seed == 12345

        # context.abort should not be called
        mock_grpc_context.abort.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_image_timeout_aborts_context(self, servicer, mock_generation_request, mock_grpc_context):
        """Should abort context when processing times out"""
        # Mock _wait_for_job_result to return None (simulating timeout)
        servicer._wait_for_job_result = AsyncMock(return_value=None)
        servicer._submit_job_to_queue = AsyncMock()  # Mock to avoid redis set issue

        # No worker simulation, will timeout
        await servicer.GenerateImage(mock_generation_request, mock_grpc_context)

        # Verify abort was called with timeout
        mock_grpc_context.abort.assert_called_once()
        call_args = mock_grpc_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.DEADLINE_EXCEEDED

    @pytest.mark.asyncio
    async def test_generate_image_handles_redis_error(self, servicer, mock_generation_request, mock_grpc_context):
        """Should abort context with INTERNAL error on Redis exception"""
        # Mock redis client to raise error
        servicer.redis_client = AsyncMock()
        servicer.redis_client.set.side_effect = Exception("Redis connection error")

        await servicer.GenerateImage(mock_generation_request, mock_grpc_context)

        # Verify abort was called with internal error
        mock_grpc_context.abort.assert_called_once()
        call_args = mock_grpc_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.INTERNAL

    @pytest.mark.asyncio
    async def test_generate_image_uses_uuid_when_no_request_id(self, servicer, fake_redis, mock_generation_request, mock_grpc_context):
        """Should generate UUID when request_id is not provided"""
        mock_generation_request.request_id = ""  # Empty request_id

        # Simulate worker
        async def simulate_worker():
            await asyncio.sleep(0.2)
            # Find the job_id that was submitted
            queue_items = await fake_redis.lrange("test_job_queue", 0, -1)
            if queue_items:
                job_id = queue_items[0].decode()
                result_channel = f"result_channel:{job_id}"
                result_key = f"result:{job_id}"
                result_data = {'image_data': b'test', 'used_seed': 1}
                await fake_redis.set(result_key, msgpack.packb(result_data, use_bin_type=True))
                await fake_redis.publish(result_channel, 'SUCCESS')

        worker_task = asyncio.create_task(simulate_worker())

        response = await servicer.GenerateImage(mock_generation_request, mock_grpc_context)

        await worker_task

        # Should have generated a UUID
        assert response.request_id != ""
        assert len(response.request_id) > 0


class TestCreateWorkerSubprocess:
    """Test create_worker_subprocess function"""

    @patch('multiprocessing.Process')
    @patch('interface.diffusion_service.RedisSDAdapter')
    def test_creates_process_with_correct_parameters(self, mock_adapter, mock_process_class):
        """Should create multiprocessing.Process with correct parameters"""
        mock_process = Mock()
        mock_process_class.return_value = mock_process

        config_path = "./test_config.ini"
        worker_type = "sd_worker"
        process_name = "TestWorker"

        result = create_worker_subprocess(config_path, worker_type, process_name)

        # Verify Process was created with correct args
        mock_process_class.assert_called_once()
        call_kwargs = mock_process_class.call_args[1]

        assert call_kwargs['target'] == mock_adapter.run_adapter_in_subprocess
        assert call_kwargs['args'] == (config_path,)
        assert call_kwargs['kwargs']['worker_type'] == worker_type
        assert call_kwargs['name'] == process_name

        # Should return the process
        assert result == mock_process

    @patch('multiprocessing.Process')
    @patch('interface.diffusion_service.RedisSDAdapter')
    def test_returns_process_instance(self, mock_adapter, mock_process_class):
        """Should return multiprocessing.Process instance"""
        mock_process = Mock()
        mock_process_class.return_value = mock_process

        result = create_worker_subprocess("./config.ini", "worker", "Worker_0")

        assert result is mock_process
