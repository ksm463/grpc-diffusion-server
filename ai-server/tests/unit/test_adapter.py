"""
Tests for worker/adapter.py

This module tests the RedisSDAdapter class which bridges Redis queue and SD Worker.
"""
import pytest
import asyncio
import msgpack
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import fakeredis
import redis


class TestRedisSDAdapterInit:
    """Test RedisSDAdapter initialization"""

    @pytest.fixture
    def mock_sd_worker_class(self):
        """Mock StableDiffusionWorker class"""
        with patch('worker.adpater.StableDiffusionWorker') as mock_class:
            mock_instance = Mock()
            mock_instance.input_queue = AsyncMock()
            mock_instance.output_queue = AsyncMock()
            mock_instance.asyncio_event = AsyncMock()
            mock_class.return_value = mock_instance
            yield mock_class

    @pytest.fixture
    def sample_sd_worker_params(self):
        """Sample SD worker parameters"""
        return {
            'queue_key': 'test_queue',
            'model_path': '/path/to/model',
            'queue_length': 200,
            'device_id': 0
        }

    @pytest.fixture
    def sample_redis_params_tcp(self):
        """Sample Redis connection parameters for TCP"""
        return {
            'use_uds': False,
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'timeout': 5
        }

    @pytest.fixture
    def sample_redis_params_uds(self):
        """Sample Redis connection parameters for UDS"""
        return {
            'use_uds': True,
            'uds_path': '/tmp/redis.sock',
            'db': 0,
            'timeout': 5
        }

    @patch('worker.adpater.redis.Redis')
    def test_initializes_with_correct_attributes(
        self, mock_redis_class, mock_sd_worker_class,
        sample_sd_worker_params, sample_redis_params_tcp
    ):
        """Should initialize with correct attributes"""
        from worker.adpater import RedisSDAdapter

        # Setup Redis mock
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_class.return_value = mock_redis_instance

        # Create adapter
        adapter = RedisSDAdapter(
            sd_worker_params=sample_sd_worker_params,
            redis_connection_params=sample_redis_params_tcp,
            redis_result_prefix='result:',
            redis_result_channel_prefix='channel:',
            redis_ttl=300
        )

        # Verify attributes
        assert adapter.redis_queue_key == 'test_queue'
        assert adapter.redis_result_prefix == 'result:'
        assert adapter.redis_result_channel_prefix == 'channel:'
        assert adapter.redis_ttl == 300
        assert adapter.redis_client == mock_redis_instance
        assert adapter._is_running is False
        assert adapter._tasks == []
        assert adapter.loop is None

    @patch('worker.adpater.redis.Redis')
    def test_creates_sd_worker_with_correct_params(
        self, mock_redis_class, mock_sd_worker_class,
        sample_sd_worker_params, sample_redis_params_tcp
    ):
        """Should create SD worker with correct parameters"""
        from worker.adpater import RedisSDAdapter

        # Setup mocks
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_class.return_value = mock_redis_instance

        # Create adapter
        adapter = RedisSDAdapter(
            sd_worker_params=sample_sd_worker_params,
            redis_connection_params=sample_redis_params_tcp,
            redis_result_prefix='result:',
            redis_result_channel_prefix='channel:',
            redis_ttl=300
        )

        # Verify SD worker was created with correct params
        mock_sd_worker_class.assert_called_once()
        call_kwargs = mock_sd_worker_class.call_args[1]
        assert call_kwargs['model_path'] == '/path/to/model'
        assert call_kwargs['queue_length'] == 200
        assert call_kwargs['device_id'] == 0

    @patch('worker.adpater.redis.Redis')
    def test_uses_custom_logger_when_provided(
        self, mock_redis_class, mock_sd_worker_class,
        sample_sd_worker_params, sample_redis_params_tcp
    ):
        """Should use custom logger instance when provided"""
        from worker.adpater import RedisSDAdapter

        # Setup mocks
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_class.return_value = mock_redis_instance

        custom_logger = Mock()

        # Create adapter with custom logger
        adapter = RedisSDAdapter(
            sd_worker_params=sample_sd_worker_params,
            redis_connection_params=sample_redis_params_tcp,
            redis_result_prefix='result:',
            redis_result_channel_prefix='channel:',
            redis_ttl=300,
            logger_instance=custom_logger
        )

        assert adapter.logger == custom_logger


class TestInitializeRedisClient:
    """Test _initialize_redis_client method"""

    @pytest.fixture
    def mock_sd_worker_class(self):
        """Mock StableDiffusionWorker class"""
        with patch('worker.adpater.StableDiffusionWorker') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            yield mock_class

    @patch('worker.adpater.redis.Redis')
    def test_creates_tcp_redis_client_with_correct_params(
        self, mock_redis_class, mock_sd_worker_class
    ):
        """Should create TCP Redis client with correct parameters"""
        from worker.adpater import RedisSDAdapter

        # Setup mock
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_class.return_value = mock_redis_instance

        redis_params = {
            'use_uds': False,
            'host': 'redis.example.com',
            'port': 6380,
            'db': 1,
            'timeout': 10
        }

        adapter = RedisSDAdapter(
            sd_worker_params={'queue_key': 'test', 'model_path': '/model'},
            redis_connection_params=redis_params,
            redis_result_prefix='result:',
            redis_result_channel_prefix='channel:',
            redis_ttl=300
        )

        # Verify Redis client was created with correct params
        mock_redis_class.assert_called_once_with(
            host='redis.example.com',
            port=6380,
            db=1,
            decode_responses=False,
            socket_connect_timeout=10
        )
        mock_redis_instance.ping.assert_called_once()

    @patch('worker.adpater.redis.Redis')
    def test_creates_uds_redis_client_with_correct_params(
        self, mock_redis_class, mock_sd_worker_class
    ):
        """Should create UDS Redis client with correct parameters"""
        from worker.adpater import RedisSDAdapter

        # Setup mock
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_class.return_value = mock_redis_instance

        redis_params = {
            'use_uds': True,
            'uds_path': '/var/run/redis.sock',
            'db': 2,
            'timeout': 15
        }

        adapter = RedisSDAdapter(
            sd_worker_params={'queue_key': 'test', 'model_path': '/model'},
            redis_connection_params=redis_params,
            redis_result_prefix='result:',
            redis_result_channel_prefix='channel:',
            redis_ttl=300
        )

        # Verify Redis client was created with UDS params
        mock_redis_class.assert_called_once_with(
            unix_socket_path='/var/run/redis.sock',
            db=2,
            decode_responses=False,
            socket_connect_timeout=15
        )
        mock_redis_instance.ping.assert_called_once()

    @patch('worker.adpater.redis.Redis')
    def test_raises_on_redis_connection_error(self, mock_redis_class, mock_sd_worker_class):
        """Should raise exception when Redis connection fails"""
        from worker.adpater import RedisSDAdapter

        # Setup mock to raise ConnectionError
        mock_redis_instance = Mock()
        mock_redis_instance.ping.side_effect = redis.exceptions.ConnectionError("Connection refused")
        mock_redis_class.return_value = mock_redis_instance

        redis_params = {
            'use_uds': False,
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'timeout': 5
        }

        # Should raise ConnectionError
        with pytest.raises(redis.exceptions.ConnectionError):
            adapter = RedisSDAdapter(
                sd_worker_params={'queue_key': 'test', 'model_path': '/model'},
                redis_connection_params=redis_params,
                redis_result_prefix='result:',
                redis_result_channel_prefix='channel:',
                redis_ttl=300
            )

    @patch('worker.adpater.redis.Redis')
    def test_raises_on_unexpected_error(self, mock_redis_class, mock_sd_worker_class):
        """Should raise exception on unexpected error during initialization"""
        from worker.adpater import RedisSDAdapter

        # Setup mock to raise generic exception
        mock_redis_instance = Mock()
        mock_redis_instance.ping.side_effect = ValueError("Unexpected error")
        mock_redis_class.return_value = mock_redis_instance

        redis_params = {
            'use_uds': False,
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'timeout': 5
        }

        # Should raise the exception
        with pytest.raises(ValueError):
            adapter = RedisSDAdapter(
                sd_worker_params={'queue_key': 'test', 'model_path': '/model'},
                redis_connection_params=redis_params,
                redis_result_prefix='result:',
                redis_result_channel_prefix='channel:',
                redis_ttl=300
            )


class TestFetchJobsFromRedis:
    """Test _fetch_jobs_from_redis method"""

    @pytest.fixture
    async def adapter_with_fake_redis(self):
        """Create adapter with fake Redis"""
        with patch('worker.adpater.StableDiffusionWorker') as mock_worker_class:
            # Mock SD worker
            mock_worker = Mock()
            mock_worker.input_queue = asyncio.Queue()
            mock_worker.output_queue = asyncio.Queue()
            mock_worker.asyncio_event = asyncio.Event()
            mock_worker_class.return_value = mock_worker

            with patch('worker.adpater.redis.Redis') as mock_redis_class:
                # Use fake redis (synchronous version)
                fake_redis = fakeredis.FakeStrictRedis(decode_responses=False)

                # Mock the Redis class to return our fake redis
                mock_redis_class.return_value = fake_redis

                from worker.adpater import RedisSDAdapter

                adapter = RedisSDAdapter(
                    sd_worker_params={'queue_key': 'job_queue', 'model_path': '/model'},
                    redis_connection_params={
                        'use_uds': False,
                        'host': 'localhost',
                        'port': 6379,
                        'db': 0,
                        'timeout': 5
                    },
                    redis_result_prefix='result:',
                    redis_result_channel_prefix='channel:',
                    redis_ttl=300
                )

                adapter.redis_client = fake_redis
                adapter._is_running = True
                adapter.loop = asyncio.get_running_loop()

                yield adapter

                adapter._is_running = False

    @pytest.mark.asyncio
    async def test_fetches_job_from_redis_and_puts_in_worker_queue(self, adapter_with_fake_redis):
        """Should fetch job from Redis and put into worker input queue"""
        adapter = adapter_with_fake_redis

        # Prepare job data
        job_id = 'test-job-123'
        job_data = {
            'job_id': job_id,
            'prompt': 'a beautiful landscape',
            'seed': 42,
            'width': 512,
            'height': 512
        }

        # Store job in Redis
        packed_job = msgpack.packb(job_data, use_bin_type=True)
        adapter.redis_client.set(f'job:{job_id}', packed_job)
        adapter.redis_client.lpush('job_queue', job_id)

        # Start fetch loop in background
        fetch_task = asyncio.create_task(adapter._fetch_jobs_from_redis())

        # Wait a bit for job to be processed
        await asyncio.sleep(0.2)

        # Stop the loop
        adapter._is_running = False
        await fetch_task

        # Verify job was put into worker queue
        assert not adapter.sd_worker.input_queue.empty()
        worker_item = await adapter.sd_worker.input_queue.get()

        assert worker_item['job_id'] == job_id
        assert worker_item['prompt'] == 'a beautiful landscape'
        assert worker_item['seed'] == 42
        assert 'timings' in worker_item
        assert 'adapter_enqueue_time' in worker_item['timings']

    @pytest.mark.asyncio
    async def test_handles_missing_job_data(self, adapter_with_fake_redis):
        """Should handle case where job_id exists but job data doesn't"""
        adapter = adapter_with_fake_redis

        # Push job_id without storing job data
        job_id = 'missing-job-456'
        adapter.redis_client.lpush('job_queue', job_id)

        # Start fetch loop
        fetch_task = asyncio.create_task(adapter._fetch_jobs_from_redis())

        await asyncio.sleep(0.2)

        adapter._is_running = False
        await fetch_task

        # Worker queue should be empty
        assert adapter.sd_worker.input_queue.empty()

    @pytest.mark.asyncio
    async def test_continues_on_empty_queue(self, adapter_with_fake_redis):
        """Should continue running when queue is empty"""
        adapter = adapter_with_fake_redis

        # Start fetch loop with empty queue
        fetch_task = asyncio.create_task(adapter._fetch_jobs_from_redis())

        await asyncio.sleep(0.1)

        # Should still be running
        assert not fetch_task.done()

        adapter._is_running = False
        await fetch_task

    @pytest.mark.asyncio
    async def test_handles_missing_job_id_with_default(self, adapter_with_fake_redis):
        """Should still process job when job_id field is missing"""
        adapter = adapter_with_fake_redis

        # Create job data without job_id field
        job_id = 'incomplete-job-789'
        incomplete_job_data = {
            'prompt': 'test',
            # Missing 'job_id' field
        }

        packed_job = msgpack.packb(incomplete_job_data, use_bin_type=True)
        adapter.redis_client.set(f'job:{job_id}', packed_job)
        adapter.redis_client.lpush('job_queue', job_id)

        # Start fetch loop
        fetch_task = asyncio.create_task(adapter._fetch_jobs_from_redis())

        await asyncio.sleep(0.2)

        adapter._is_running = False
        await fetch_task

        # Worker queue should have the job (without job_id field)
        assert not adapter.sd_worker.input_queue.empty()
        worker_item = await adapter.sd_worker.input_queue.get()
        assert worker_item['prompt'] == 'test'
        assert 'job_id' not in worker_item  # job_id was not in original data

    @pytest.mark.asyncio
    async def test_continues_after_exception_in_fetch_loop(self, adapter_with_fake_redis):
        """Should continue running after exception in fetch loop"""
        adapter = adapter_with_fake_redis

        # Put invalid msgpack data to trigger exception
        job_id = 'invalid-msgpack-job'
        adapter.redis_client.set(f'job:{job_id}', b'invalid_msgpack_data')
        adapter.redis_client.lpush('job_queue', job_id)

        # Start fetch loop
        fetch_task = asyncio.create_task(adapter._fetch_jobs_from_redis())

        await asyncio.sleep(0.2)

        # Should still be running despite exception
        adapter._is_running = False
        await fetch_task

        # Worker queue should be empty
        assert adapter.sd_worker.input_queue.empty()


class TestPublishResultsToRedis:
    """Test _publish_results_to_redis method"""

    @pytest.fixture
    async def adapter_with_fake_redis(self):
        """Create adapter with fake Redis"""
        with patch('worker.adpater.StableDiffusionWorker') as mock_worker_class:
            # Mock SD worker
            mock_worker = Mock()
            mock_worker.input_queue = asyncio.Queue()
            mock_worker.output_queue = asyncio.Queue()
            mock_worker.asyncio_event = asyncio.Event()
            mock_worker_class.return_value = mock_worker

            with patch('worker.adpater.redis.Redis') as mock_redis_class:
                # Use fake redis
                fake_redis = fakeredis.FakeStrictRedis(decode_responses=False)
                mock_redis_class.return_value = fake_redis

                from worker.adpater import RedisSDAdapter

                adapter = RedisSDAdapter(
                    sd_worker_params={'queue_key': 'job_queue', 'model_path': '/model'},
                    redis_connection_params={
                        'use_uds': False,
                        'host': 'localhost',
                        'port': 6379,
                        'db': 0,
                        'timeout': 5
                    },
                    redis_result_prefix='result:',
                    redis_result_channel_prefix='channel:',
                    redis_ttl=300
                )

                adapter.redis_client = fake_redis
                adapter._is_running = True
                adapter.loop = asyncio.get_running_loop()

                yield adapter

                adapter._is_running = False

    @pytest.mark.asyncio
    async def test_publishes_success_result_to_redis(self, adapter_with_fake_redis):
        """Should publish successful result to Redis"""
        adapter = adapter_with_fake_redis

        # Prepare success result
        job_id = 'success-job-789'
        result_data = {
            'job_id': job_id,
            'status': 'success',
            'image_data': b'fake_image_bytes',
            'used_seed': 12345
        }

        # Put result into worker output queue
        await adapter.sd_worker.output_queue.put(result_data)

        # Start publish loop
        publish_task = asyncio.create_task(adapter._publish_results_to_redis())

        await asyncio.sleep(0.2)

        adapter._is_running = False
        # Wait for queue to be empty
        await adapter.sd_worker.output_queue.join()
        await publish_task

        # Verify result was stored in Redis
        result_key = f'result:{job_id}'
        stored_result = adapter.redis_client.get(result_key)

        assert stored_result is not None
        unpacked_result = msgpack.unpackb(stored_result, raw=False)
        assert unpacked_result['image_data'] == b'fake_image_bytes'
        assert unpacked_result['used_seed'] == 12345

    @pytest.mark.asyncio
    async def test_publishes_error_result_to_redis(self, adapter_with_fake_redis):
        """Should publish error result to Redis"""
        adapter = adapter_with_fake_redis

        # Prepare error result
        job_id = 'error-job-999'
        result_data = {
            'job_id': job_id,
            'status': 'error',
            'error_message': 'Model loading failed'
        }

        # Put error into worker output queue
        await adapter.sd_worker.output_queue.put(result_data)

        # Start publish loop
        publish_task = asyncio.create_task(adapter._publish_results_to_redis())

        await asyncio.sleep(0.2)

        adapter._is_running = False
        await adapter.sd_worker.output_queue.join()
        await publish_task

        # Verify error was stored in Redis
        result_key = f'result:{job_id}'
        stored_error = adapter.redis_client.get(result_key)

        assert stored_error is not None
        unpacked_error = msgpack.unpackb(stored_error, raw=False)
        assert 'error' in unpacked_error
        assert 'Model loading failed' in unpacked_error['error']

    @pytest.mark.asyncio
    async def test_skips_result_without_job_id(self, adapter_with_fake_redis):
        """Should skip result that has no job_id"""
        adapter = adapter_with_fake_redis

        # Result without job_id
        result_data = {
            'status': 'success',
            'image_data': b'fake_image'
        }

        await adapter.sd_worker.output_queue.put(result_data)

        publish_task = asyncio.create_task(adapter._publish_results_to_redis())

        await asyncio.sleep(0.2)

        adapter._is_running = False
        await adapter.sd_worker.output_queue.join()
        await publish_task

        # No result should be stored (no job_id to create key)
        # Queue should be processed (task_done called)
        assert adapter.sd_worker.output_queue.empty()

    @pytest.mark.asyncio
    async def test_handles_cancelled_error_in_publish_loop(self, adapter_with_fake_redis):
        """Should handle CancelledError gracefully in publish loop"""
        adapter = adapter_with_fake_redis

        # Start publish loop
        publish_task = asyncio.create_task(adapter._publish_results_to_redis())

        await asyncio.sleep(0.1)

        # Cancel the task
        publish_task.cancel()

        # Should not raise exception
        try:
            await publish_task
        except asyncio.CancelledError:
            # This is expected
            pass

        # Should complete without error
        assert publish_task.done()

    @pytest.mark.asyncio
    async def test_continues_after_exception_in_publish_loop(self, adapter_with_fake_redis):
        """Should continue processing after exception in publish loop"""
        adapter = adapter_with_fake_redis

        # Put a result that will cause exception (missing required fields)
        bad_result = {
            'job_id': 'bad-job-123',
            'status': 'success',
            # Missing 'image_data' and 'used_seed'
        }

        await adapter.sd_worker.output_queue.put(bad_result)

        # Put a good result after the bad one
        good_result = {
            'job_id': 'good-job-456',
            'status': 'success',
            'image_data': b'good_image',
            'used_seed': 999
        }
        await adapter.sd_worker.output_queue.put(good_result)

        # Start publish loop
        publish_task = asyncio.create_task(adapter._publish_results_to_redis())

        await asyncio.sleep(0.3)

        adapter._is_running = False
        await adapter.sd_worker.output_queue.join()
        await publish_task

        # Good result should still be published despite bad result
        good_result_key = f'result:good-job-456'
        stored_good = adapter.redis_client.get(good_result_key)
        assert stored_good is not None


class TestPublishErrorToRedis:
    """Test _publish_error_to_redis method"""

    @pytest.fixture
    async def adapter_with_fake_redis(self):
        """Create adapter with fake Redis"""
        with patch('worker.adpater.StableDiffusionWorker') as mock_worker_class:
            mock_worker = Mock()
            mock_worker_class.return_value = mock_worker

            with patch('worker.adpater.redis.Redis') as mock_redis_class:
                fake_redis = fakeredis.FakeStrictRedis(decode_responses=False)
                mock_redis_class.return_value = fake_redis

                from worker.adpater import RedisSDAdapter

                adapter = RedisSDAdapter(
                    sd_worker_params={'queue_key': 'job_queue', 'model_path': '/model'},
                    redis_connection_params={
                        'use_uds': False,
                        'host': 'localhost',
                        'port': 6379,
                        'db': 0
                    },
                    redis_result_prefix='result:',
                    redis_result_channel_prefix='channel:',
                    redis_ttl=300
                )

                adapter.redis_client = fake_redis
                adapter.loop = asyncio.get_running_loop()

                yield adapter

    @pytest.mark.asyncio
    async def test_publishes_error_message_to_redis(self, adapter_with_fake_redis):
        """Should publish error message to Redis"""
        adapter = adapter_with_fake_redis

        job_id = 'error-test-job'
        error_message = 'Critical error in processing'

        await adapter._publish_error_to_redis(job_id, error_message)

        # Verify error was stored
        result_key = f'result:{job_id}'
        stored_error = adapter.redis_client.get(result_key)

        assert stored_error is not None
        unpacked_error = msgpack.unpackb(stored_error, raw=False)
        assert unpacked_error['error'] == error_message

    @pytest.mark.asyncio
    async def test_handles_exception_in_publish_error(self):
        """Should handle exception when publishing error to Redis fails"""
        with patch('worker.adpater.StableDiffusionWorker') as mock_worker_class:
            mock_worker = Mock()
            mock_worker_class.return_value = mock_worker

            with patch('worker.adpater.redis.Redis') as mock_redis_class:
                # Create mock redis that raises exception
                mock_redis = Mock()
                mock_redis.ping.return_value = True
                mock_redis.set.side_effect = Exception("Redis connection lost")
                mock_redis.publish.side_effect = Exception("Redis connection lost")
                mock_redis_class.return_value = mock_redis

                from worker.adpater import RedisSDAdapter

                adapter = RedisSDAdapter(
                    sd_worker_params={'queue_key': 'job_queue', 'model_path': '/model'},
                    redis_connection_params={
                        'use_uds': False,
                        'host': 'localhost',
                        'port': 6379,
                        'db': 0
                    },
                    redis_result_prefix='result:',
                    redis_result_channel_prefix='channel:',
                    redis_ttl=300
                )

                adapter.loop = asyncio.get_running_loop()

                # Should not raise exception
                await adapter._publish_error_to_redis('test-job', 'error message')

                # Redis operations should have been attempted
                assert mock_redis.set.called or mock_redis.publish.called


class TestStartStop:
    """Test start and stop methods"""

    @pytest.fixture
    async def adapter_with_mocks(self):
        """Create adapter with all mocked dependencies"""
        with patch('worker.adpater.StableDiffusionWorker') as mock_worker_class:
            # Mock SD worker
            mock_worker = Mock()
            mock_worker.input_queue = asyncio.Queue()
            mock_worker.output_queue = asyncio.Queue()
            mock_worker.asyncio_event = asyncio.Event()
            mock_worker.asyncio_event.set()  # Simulate worker ready
            mock_worker.start = AsyncMock()
            mock_worker_class.return_value = mock_worker

            with patch('worker.adpater.redis.Redis') as mock_redis_class:
                fake_redis = fakeredis.FakeStrictRedis(decode_responses=False)
                mock_redis_class.return_value = fake_redis

                from worker.adpater import RedisSDAdapter

                adapter = RedisSDAdapter(
                    sd_worker_params={'queue_key': 'job_queue', 'model_path': '/model'},
                    redis_connection_params={
                        'use_uds': False,
                        'host': 'localhost',
                        'port': 6379,
                        'db': 0
                    },
                    redis_result_prefix='result:',
                    redis_result_channel_prefix='channel:',
                    redis_ttl=300
                )

                adapter.redis_client = fake_redis

                yield adapter

    @pytest.mark.asyncio
    async def test_start_creates_tasks(self, adapter_with_mocks):
        """Should create necessary tasks when started"""
        adapter = adapter_with_mocks

        await adapter.start()

        # Should be running
        assert adapter._is_running is True
        assert adapter.loop is not None

        # Should have created tasks
        assert len(adapter._tasks) == 3  # SD worker, fetch, publish

        # Cleanup
        await adapter.stop()

    @pytest.mark.asyncio
    async def test_start_does_nothing_when_already_running(self, adapter_with_mocks):
        """Should not restart when already running"""
        adapter = adapter_with_mocks

        await adapter.start()
        task_count_first = len(adapter._tasks)

        # Try to start again
        await adapter.start()
        task_count_second = len(adapter._tasks)

        # Task count should not change
        assert task_count_first == task_count_second

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_tasks(self, adapter_with_mocks):
        """Should cancel all tasks when stopped"""
        adapter = adapter_with_mocks

        await adapter.start()
        assert adapter._is_running is True
        assert len(adapter._tasks) > 0

        await adapter.stop()

        assert adapter._is_running is False
        assert len(adapter._tasks) == 0

    @pytest.mark.asyncio
    async def test_stop_does_nothing_when_not_running(self, adapter_with_mocks):
        """Should handle stop when not running"""
        adapter = adapter_with_mocks

        # Stop without starting
        await adapter.stop()

        assert adapter._is_running is False
        assert len(adapter._tasks) == 0

    @pytest.mark.asyncio
    async def test_start_logs_warning_when_worker_event_not_set(self):
        """Should log warning when SD worker event is not set after start"""
        with patch('worker.adpater.StableDiffusionWorker') as mock_worker_class:
            # Mock SD worker with event NOT set
            mock_worker = Mock()
            mock_worker.input_queue = asyncio.Queue()
            mock_worker.output_queue = asyncio.Queue()
            mock_worker.asyncio_event = asyncio.Event()
            # Do NOT set the event - simulating worker not ready
            mock_worker.start = AsyncMock()
            mock_worker_class.return_value = mock_worker

            with patch('worker.adpater.redis.Redis') as mock_redis_class:
                fake_redis = fakeredis.FakeStrictRedis(decode_responses=False)
                mock_redis_class.return_value = fake_redis

                from worker.adpater import RedisSDAdapter

                # Mock logger to capture warning
                mock_logger = Mock()

                adapter = RedisSDAdapter(
                    sd_worker_params={'queue_key': 'job_queue', 'model_path': '/model'},
                    redis_connection_params={
                        'use_uds': False,
                        'host': 'localhost',
                        'port': 6379,
                        'db': 0
                    },
                    redis_result_prefix='result:',
                    redis_result_channel_prefix='channel:',
                    redis_ttl=300,
                    logger_instance=mock_logger
                )

                adapter.redis_client = fake_redis

                # Start adapter
                await adapter.start()

                # Should have logged warning about event not being set
                warning_logged = any(
                    'asyncio_event not set' in str(call)
                    for call in mock_logger.warning.call_args_list
                )
                assert warning_logged

                await adapter.stop()
