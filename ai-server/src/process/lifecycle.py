import asyncio
import os
import signal
from typing import List, Optional, Callable
from loguru import logger


async def wait_for_workers_with_backoff(
    worker_processes: List,
    max_retries: int = 10,
    initial_delay: float = 0.1,
    max_delay: float = 5.0,
    health_check_fn: Optional[Callable] = None
) -> bool:
    """
    워커 프로세스들이 모두 살아있을 때까지 exponential backoff로 대기
    
    Args:
        worker_processes: 확인할 워커 프로세스 리스트
        max_retries: 최대 재시도 횟수
        initial_delay: 초기 대기 시간 (초)
        max_delay: 최대 대기 시간 (초)
        health_check_fn: 커스텀 헬스체크 함수 (선택적)
    
    Returns:
        bool: 모든 워커가 성공적으로 시작되면 True, 실패하면 False
    """
    delay = initial_delay
    
    # 기본 헬스체크 함수
    if health_check_fn is None:
        health_check_fn = lambda p: p.is_alive()
    
    for attempt in range(max_retries):
        all_healthy = True
        unhealthy_workers = []
        
        for p in worker_processes:
            if not health_check_fn(p):
                all_healthy = False
                unhealthy_workers.append(p.pid if hasattr(p, 'pid') else str(p))
        
        if all_healthy:
            logger.success(
                f"All {len(worker_processes)} worker processes are healthy "
                f"after {attempt + 1} attempts."
            )
            return True
        
        if attempt < max_retries - 1:
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries}: "
                f"{len(unhealthy_workers)} worker(s) not yet healthy. "
                f"PIDs: {unhealthy_workers}. Retrying in {delay:.2f} seconds..."
            )
            await asyncio.sleep(delay)
            
            # Exponential backoff with cap
            delay = min(delay * 2, max_delay)
        else:
            logger.error(
                f"Failed to start all workers after {max_retries} attempts. "
                f"Unhealthy worker PIDs: {unhealthy_workers}"
            )
    
    return False


async def graceful_shutdown_workers(
    worker_processes: List,
    timeout: float = 10.0,
    force_kill_timeout: float = 1.0
) -> None:
    """
    워커 프로세스들을 gracefully 종료
    
    Args:
        worker_processes: 종료할 워커 프로세스 리스트
        timeout: graceful shutdown 대기 시간
        force_kill_timeout: 강제 종료 후 대기 시간
    """
    if not worker_processes:
        return
    
    logger.info(f"Initiating graceful shutdown for {len(worker_processes)} workers...")
    
    # SIGTERM 전송
    alive_workers = []
    for p in worker_processes:
        if p.is_alive():
            logger.debug(f"Sending SIGTERM to worker (PID: {p.pid})")
            p.terminate()
            alive_workers.append(p)
    
    if not alive_workers:
        logger.info("No alive workers to terminate.")
        return
    
    # Graceful shutdown 대기
    start_time = asyncio.get_event_loop().time()
    while any(p.is_alive() for p in alive_workers):
        if asyncio.get_event_loop().time() - start_time > timeout:
            logger.warning(f"Graceful shutdown timeout ({timeout}s) exceeded.")
            break
        await asyncio.sleep(0.1)
    
    # 강제 종료가 필요한 워커 처리
    for p in alive_workers:
        if p.is_alive():
            logger.warning(
                f"Worker process (PID: {p.pid}) did not terminate gracefully. "
                f"Forcing kill..."
            )
            p.kill()
            p.join(timeout=force_kill_timeout)
            
            if p.is_alive():
                logger.error(f"Failed to kill worker process (PID: {p.pid})")
    
    logger.info("All worker shutdown operations completed.")


class ProcessLifecycleManager:
    """
    프로세스 생명주기를 관리하는 헬퍼 클래스
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.worker_processes = []
        self.watchdog_process = None
        
    async def start_workers(
        self,
        create_worker_fn: Callable,
        worker_count: int,
        **worker_kwargs
    ) -> bool:
        """
        워커 프로세스들을 시작하고 상태 체크 수행
        
        Args:
            create_worker_fn: 워커 생성 함수
            worker_count: 생성할 워커 수
            **worker_kwargs: 워커 생성 함수에 전달할 인자들
        
        Returns:
            bool: 성공 여부
        """
        logger.info(f"Starting {worker_count} worker processes...")
        
        for i in range(worker_count):
            process_name = f'Worker_{i}'
            worker_process = create_worker_fn(
                process_name=process_name,
                **worker_kwargs
            )
            worker_process.start()
            self.worker_processes.append(worker_process)
            logger.info(f"WORKER(PID {worker_process.pid}) - Starting...")
        
        # 워커들이 준비될 때까지 대기
        workers_ready = await wait_for_workers_with_backoff(
            self.worker_processes,
            max_retries=self.config.get('max_retries', 10),
            initial_delay=self.config.get('initial_delay', 0.1),
            max_delay=self.config.get('max_delay', 5.0)
        )
        
        if not workers_ready:
            await self.cleanup_failed_workers()
            return False
        
        return True
    
    async def cleanup_failed_workers(self):
        """
        실패한 워커들 정리
        """
        alive_workers = [p for p in self.worker_processes if p.is_alive()]
        dead_workers = [p for p in self.worker_processes if not p.is_alive()]
        
        logger.error(
            f"Worker startup failed. "
            f"Alive: {len(alive_workers)}, Dead: {len(dead_workers)}"
        )
        
        # 살아있는 워커들 종료
        await graceful_shutdown_workers(alive_workers)
        
        self.worker_processes.clear()
    
    def start_watchdog(self, create_watchdog_fn: Callable) -> None:
        """
        Watchdog 프로세스 시작
        
        Args:
            create_watchdog_fn: Watchdog 생성 함수
        """
        if not self.worker_processes:
            logger.warning("No worker processes to monitor. Skipping watchdog.")
            return
        
        logger.info("Starting watchdog process...")
        self.watchdog_process = create_watchdog_fn(
            worker_processes=self.worker_processes,
            check_interval=self.config.get('watchdog_check_interval', 2.0),
            max_restart_attempts=self.config.get('watchdog_max_restarts', 3)
        )
        logger.info(f"Watchdog process started (PID: {self.watchdog_process.pid})")
    
    async def shutdown(self):
        """
        모든 관리 중인 프로세스 종료
        """
        logger.info("Starting lifecycle manager shutdown...")
        
        # Watchdog 먼저 종료
        if self.watchdog_process and self.watchdog_process.is_alive():
            logger.info("Terminating watchdog process...")
            self.watchdog_process.terminate()
            self.watchdog_process.join(timeout=2)
            if self.watchdog_process.is_alive():
                logger.warning("Watchdog did not terminate, forcing kill...")
                self.watchdog_process.kill()
        
        # 워커 프로세스들 종료
        await graceful_shutdown_workers(
            self.worker_processes,
            timeout=self.config.get('shutdown_timeout', 10.0)
        )
        
        logger.info("Lifecycle manager shutdown complete.")