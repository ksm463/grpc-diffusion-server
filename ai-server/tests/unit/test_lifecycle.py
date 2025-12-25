"""
Tests for process/lifecycle.py
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from process.lifecycle import (
    wait_for_workers_with_backoff,
    graceful_shutdown_workers,
    ProcessLifecycleManager
)


class TestWaitForWorkersWithBackoff:
    """Test wait_for_workers_with_backoff function"""

    @pytest.mark.asyncio
    async def test_returns_true_when_all_workers_healthy_immediately(self):
        """Should return True when all workers are healthy on first check"""
        # Create mock workers that are alive
        mock_workers = []
        for i in range(3):
            mock = Mock()
            mock.is_alive.return_value = True
            mock.pid = 1000 + i
            mock_workers.append(mock)

        result = await wait_for_workers_with_backoff(
            mock_workers,
            max_retries=3,
            initial_delay=0.01,
            max_delay=0.1
        )

        assert result is True
        # Each worker should be checked once
        for worker in mock_workers:
            worker.is_alive.assert_called()

    @pytest.mark.asyncio
    async def test_returns_true_after_retries(self):
        """Should return True when workers become healthy after retries"""
        # Create mock workers that become alive after 2 attempts
        mock_workers = []
        for i in range(2):
            mock = Mock()
            # First 2 calls return False, then True
            mock.is_alive.side_effect = [False, False, True]
            mock.pid = 2000 + i
            mock_workers.append(mock)

        result = await wait_for_workers_with_backoff(
            mock_workers,
            max_retries=5,
            initial_delay=0.01,
            max_delay=0.1
        )

        assert result is True
        # Should have been called 3 times (2 failures + 1 success)
        for worker in mock_workers:
            assert worker.is_alive.call_count == 3

    @pytest.mark.asyncio
    async def test_returns_false_when_max_retries_exceeded(self):
        """Should return False when workers never become healthy"""
        # Create mock workers that are never alive
        mock_workers = []
        for i in range(2):
            mock = Mock()
            mock.is_alive.return_value = False
            mock.pid = 3000 + i
            mock_workers.append(mock)

        result = await wait_for_workers_with_backoff(
            mock_workers,
            max_retries=3,
            initial_delay=0.01,
            max_delay=0.1
        )

        assert result is False
        # Should have been checked max_retries times
        for worker in mock_workers:
            assert worker.is_alive.call_count == 3

    @pytest.mark.asyncio
    async def test_uses_exponential_backoff(self):
        """Should use exponential backoff with max_delay cap"""
        mock_worker = Mock()
        mock_worker.is_alive.side_effect = [False, False, False, True]
        mock_worker.pid = 4000

        start_time = asyncio.get_event_loop().time()
        result = await wait_for_workers_with_backoff(
            [mock_worker],
            max_retries=4,
            initial_delay=0.1,
            max_delay=0.3
        )
        elapsed = asyncio.get_event_loop().time() - start_time

        assert result is True
        # Should have waited: 0.1 + 0.2 + 0.3 = 0.6 seconds minimum
        assert elapsed >= 0.5

    @pytest.mark.asyncio
    async def test_uses_custom_health_check_function(self):
        """Should use custom health check function when provided"""
        mock_worker = Mock()
        mock_worker.custom_status = True
        mock_worker.pid = 5000

        # Custom health check function
        def custom_check(worker):
            return worker.custom_status

        result = await wait_for_workers_with_backoff(
            [mock_worker],
            max_retries=1,
            health_check_fn=custom_check
        )

        assert result is True
        # is_alive should not be called when custom function is provided
        mock_worker.is_alive.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_worker_without_pid_attribute(self):
        """Should handle workers without pid attribute gracefully"""
        mock_worker = Mock()
        mock_worker.is_alive.return_value = False
        # Remove pid attribute
        del mock_worker.pid

        result = await wait_for_workers_with_backoff(
            [mock_worker],
            max_retries=2,
            initial_delay=0.01
        )

        assert result is False
        # Should not crash when accessing pid


class TestGracefulShutdownWorkers:
    """Test graceful_shutdown_workers function"""

    @pytest.mark.asyncio
    async def test_terminates_alive_workers(self):
        """Should send SIGTERM to alive workers"""
        mock_workers = []
        for i in range(3):
            mock = Mock()
            # Simulate worker terminating gracefully
            # First call (alive check), then terminate, then dead
            mock.is_alive.side_effect = [True, False, False]
            mock.pid = 6000 + i
            mock.terminate = Mock()
            mock.kill = Mock()
            mock_workers.append(mock)

        await graceful_shutdown_workers(
            mock_workers,
            timeout=1.0,
            force_kill_timeout=0.1
        )

        # All workers should have terminate called
        for worker in mock_workers:
            worker.terminate.assert_called_once()
            # Should not need to kill since they terminated gracefully
            worker.kill.assert_not_called()

    @pytest.mark.asyncio
    async def test_kills_workers_that_do_not_terminate(self):
        """Should force kill workers that don't terminate within timeout"""
        mock_worker = Mock()
        # Worker stays alive through timeout
        mock_worker.is_alive.return_value = True
        mock_worker.pid = 7000
        mock_worker.terminate = Mock()
        mock_worker.kill = Mock()
        mock_worker.join = Mock()

        await graceful_shutdown_workers(
            [mock_worker],
            timeout=0.1,
            force_kill_timeout=0.05
        )

        # Should have called both terminate and kill
        mock_worker.terminate.assert_called_once()
        mock_worker.kill.assert_called_once()
        mock_worker.join.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_early_when_no_workers(self):
        """Should return immediately when worker list is empty"""
        # Should not raise any errors
        await graceful_shutdown_workers([], timeout=1.0)

    @pytest.mark.asyncio
    async def test_skips_already_dead_workers(self):
        """Should not terminate workers that are already dead"""
        mock_dead_worker = Mock()
        mock_dead_worker.is_alive.return_value = False
        mock_dead_worker.pid = 8000
        mock_dead_worker.terminate = Mock()

        mock_alive_worker = Mock()
        mock_alive_worker.is_alive.side_effect = [True, False, False]
        mock_alive_worker.pid = 8001
        mock_alive_worker.terminate = Mock()
        mock_alive_worker.kill = Mock()

        await graceful_shutdown_workers(
            [mock_dead_worker, mock_alive_worker],
            timeout=1.0
        )

        # Dead worker should not be terminated
        mock_dead_worker.terminate.assert_not_called()
        # Alive worker should be terminated
        mock_alive_worker.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_waits_for_graceful_shutdown(self):
        """Should wait for workers to terminate gracefully before force kill"""
        mock_worker = Mock()
        # Worker terminates after 2 checks in while loop
        # First: alive check (True), second: while loop (True), third: while loop (False), fourth: force kill check (False)
        mock_worker.is_alive.side_effect = [True, True, False, False]
        mock_worker.pid = 9000
        mock_worker.terminate = Mock()
        mock_worker.kill = Mock()

        start_time = asyncio.get_event_loop().time()
        await graceful_shutdown_workers(
            [mock_worker],
            timeout=1.0,
            force_kill_timeout=0.1
        )
        elapsed = asyncio.get_event_loop().time() - start_time

        # Should have waited at least 0.1 seconds
        assert elapsed >= 0.1
        mock_worker.terminate.assert_called_once()
        # Should not need to kill
        mock_worker.kill.assert_not_called()


class TestProcessLifecycleManager:
    """Test ProcessLifecycleManager class"""

    @pytest.fixture
    def lifecycle_config(self):
        """Sample configuration for lifecycle manager"""
        return {
            'max_retries': 3,
            'initial_delay': 0.01,
            'max_delay': 0.1,
            'shutdown_timeout': 1.0,
            'watchdog_check_interval': 0.1,
            'watchdog_max_restarts': 3
        }

    @pytest.fixture
    def lifecycle_manager(self, lifecycle_config):
        """Create ProcessLifecycleManager instance"""
        return ProcessLifecycleManager(lifecycle_config)

    @pytest.mark.asyncio
    async def test_start_workers_successfully(self, lifecycle_manager):
        """Should successfully start workers and return True"""
        def create_mock_worker(process_name, **kwargs):
            mock = Mock()
            mock.is_alive.return_value = True
            mock.pid = hash(process_name) % 100000
            mock.start = Mock()
            return mock

        result = await lifecycle_manager.start_workers(
            create_worker_fn=create_mock_worker,
            worker_count=2,
            config_path='./test.ini'
        )

        assert result is True
        assert len(lifecycle_manager.worker_processes) == 2
        # All workers should have been started
        for worker in lifecycle_manager.worker_processes:
            worker.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_workers_fails_when_workers_not_healthy(self, lifecycle_manager):
        """Should return False and cleanup when workers fail to start"""
        def create_failing_worker(process_name, **kwargs):
            mock = Mock()
            mock.is_alive.return_value = False
            mock.pid = hash(process_name) % 100000
            mock.start = Mock()
            mock.terminate = Mock()
            return mock

        result = await lifecycle_manager.start_workers(
            create_worker_fn=create_failing_worker,
            worker_count=2,
            config_path='./test.ini'
        )

        assert result is False
        # Worker list should be cleared after cleanup
        assert len(lifecycle_manager.worker_processes) == 0

    @pytest.mark.asyncio
    async def test_cleanup_failed_workers(self, lifecycle_manager):
        """Should cleanup alive workers when some workers fail"""
        # Create some alive and some dead workers
        alive_worker = Mock()
        # is_alive called multiple times: filter check (True), alive workers (True), terminate check (True), while loop (False), force kill check (False)
        alive_worker.is_alive.side_effect = [True, True, True, False, False]
        alive_worker.pid = 10000
        alive_worker.terminate = Mock()
        alive_worker.kill = Mock()

        dead_worker = Mock()
        dead_worker.is_alive.return_value = False
        dead_worker.pid = 10001

        lifecycle_manager.worker_processes = [alive_worker, dead_worker]

        await lifecycle_manager.cleanup_failed_workers()

        # Alive worker should be terminated
        alive_worker.terminate.assert_called_once()
        # Worker list should be cleared
        assert len(lifecycle_manager.worker_processes) == 0

    def test_start_watchdog(self, lifecycle_manager):
        """Should start watchdog process"""
        # Add some workers first
        mock_worker = Mock()
        mock_worker.pid = 11000
        lifecycle_manager.worker_processes = [mock_worker]

        def create_mock_watchdog(worker_processes, check_interval, max_restart_attempts):
            mock = Mock()
            mock.pid = 11500
            return mock

        lifecycle_manager.start_watchdog(create_watchdog_fn=create_mock_watchdog)

        assert lifecycle_manager.watchdog_process is not None
        assert lifecycle_manager.watchdog_process.pid == 11500

    def test_start_watchdog_skips_when_no_workers(self, lifecycle_manager):
        """Should skip watchdog when no workers exist"""
        # No workers added
        def create_mock_watchdog(worker_processes, check_interval, max_restart_attempts):
            return Mock()

        lifecycle_manager.start_watchdog(create_watchdog_fn=create_mock_watchdog)

        # Watchdog should not be created
        assert lifecycle_manager.watchdog_process is None

    @pytest.mark.asyncio
    async def test_shutdown_terminates_watchdog_and_workers(self, lifecycle_manager):
        """Should shutdown watchdog and workers in correct order"""
        # Create mock watchdog
        mock_watchdog = Mock()
        mock_watchdog.is_alive.side_effect = [True, False]
        mock_watchdog.pid = 12000
        mock_watchdog.terminate = Mock()
        mock_watchdog.join = Mock()
        lifecycle_manager.watchdog_process = mock_watchdog

        # Create mock workers
        mock_worker = Mock()
        # is_alive: alive check (True), while loop (False), force kill check (False)
        mock_worker.is_alive.side_effect = [True, False, False]
        mock_worker.pid = 12100
        mock_worker.terminate = Mock()
        mock_worker.kill = Mock()
        lifecycle_manager.worker_processes = [mock_worker]

        await lifecycle_manager.shutdown()

        # Watchdog should be terminated first
        mock_watchdog.terminate.assert_called_once()
        mock_watchdog.join.assert_called_once()

        # Workers should be terminated
        mock_worker.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_force_kills_watchdog_if_needed(self, lifecycle_manager):
        """Should force kill watchdog if it doesn't terminate"""
        mock_watchdog = Mock()
        # Watchdog stays alive after terminate
        mock_watchdog.is_alive.return_value = True
        mock_watchdog.pid = 13000
        mock_watchdog.terminate = Mock()
        mock_watchdog.join = Mock()
        mock_watchdog.kill = Mock()
        lifecycle_manager.watchdog_process = mock_watchdog

        await lifecycle_manager.shutdown()

        # Should have called both terminate and kill
        mock_watchdog.terminate.assert_called_once()
        mock_watchdog.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_handles_no_processes(self, lifecycle_manager):
        """Should handle shutdown when no processes exist"""
        # No watchdog or workers
        await lifecycle_manager.shutdown()
        # Should complete without errors
