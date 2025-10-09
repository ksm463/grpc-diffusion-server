import os
import time
import signal
import multiprocessing
import sys
from typing import List, Optional
from loguru import logger


class WorkerWatchdog:
    """
    워커 프로세스들을 모니터링하고, 문제 발생 시 메인 프로세스에 알리는 감시 프로세스
    """
    
    def __init__(self, 
                 worker_pids: List[int],
                 check_interval: float = 2.0,
                 max_restart_attempts: int = 3,
                 restart_cooldown: float = 10.0):
        """
        Args:
            worker_pids: 모니터링할 워커 프로세스 PID 리스트
            check_interval: 상태 확인 주기 (초)
            max_restart_attempts: 최대 재시작 시도 횟수
            restart_cooldown: 재시작 시도 간 대기 시간 (초)
        """
        self.worker_pids = worker_pids
        self.check_interval = check_interval
        self.max_restart_attempts = max_restart_attempts
        self.restart_cooldown = restart_cooldown
        self.restart_counts = {pid: 0 for pid in worker_pids}
        self.last_restart_times = {pid: 0 for pid in worker_pids}
        self._running = False
        self._parent_pid = os.getppid()
        
    def check_process_alive(self, pid: int) -> bool:
        """프로세스가 살아있는지 확인"""
        try:
            # PID가 존재하는지 확인 (signal 0은 실제로 시그널을 보내지 않음)
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
    
    def check_parent_alive(self) -> bool:
        """부모 프로세스(메인 서버)가 살아있는지 확인"""
        return self.check_process_alive(self._parent_pid)
    
    def notify_main_process(self, message: str, critical: bool = False):
        """메인 프로세스에 상태를 알림"""
        if critical:
            logger.critical(f"{message}")
            # 메인 프로세스에 SIGTERM 전송하여 graceful shutdown 유도
            try:
                os.kill(self._parent_pid, signal.SIGTERM)
            except (OSError, ProcessLookupError):
                logger.error("Failed to signal main process - may be already dead")
        else:
            logger.warning(f"{message}")
    
    def should_attempt_restart(self, pid: int) -> bool:
        """워커 재시작을 시도해야 하는지 판단"""
        current_time = time.time()
        
        # 마지막 재시작 후 충분한 시간이 지났는지 확인
        if current_time - self.last_restart_times[pid] < self.restart_cooldown:
            return False
        
        # 재시작 시도 횟수 확인
        if self.restart_counts[pid] >= self.max_restart_attempts:
            return False
        
        return True
    
    def run(self):
        """감시 프로세스 메인 루프"""
        logger.info(f"Starting worker watchdog for PIDs: {self.worker_pids}")
        self._running = True
        consecutive_failures = 0
        last_check_log_time = time.time()
        
        while self._running:
            try:
                # 부모 프로세스가 죽었으면 watchdog도 종료
                if not self.check_parent_alive():
                    logger.warning("Parent process died, shutting down")
                    break
                
                dead_workers = []
                alive_workers = []
                
                for pid in self.worker_pids:
                    if self.check_process_alive(pid):
                        alive_workers.append(pid)
                    else:
                        dead_workers.append(pid)
                
                # 주기적으로 상태 로그 출력 (30초마다)
                current_time = time.time()
                if current_time - last_check_log_time > 30:
                    logger.debug(
                        f"Status check - Alive: {len(alive_workers)}/{len(self.worker_pids)}, "
                        f"PIDs: {alive_workers}"
                    )
                    last_check_log_time = current_time
                
                if dead_workers:
                    logger.error(
                        f"Dead workers detected: {dead_workers} "
                        f"(Alive: {len(alive_workers)}/{len(self.worker_pids)})"
                    )
                    
                    # 모든 워커가 죽었으면 즉시 시스템 종료
                    if not alive_workers:
                        self.notify_main_process(
                            "All worker processes died! Initiating emergency shutdown.",
                            critical=True
                        )
                        break
                    
                    # 일부 워커만 죽었을 때의 처리
                    recoverable = False
                    for dead_pid in dead_workers:
                        if self.should_attempt_restart(dead_pid):
                            self.restart_counts[dead_pid] += 1
                            self.last_restart_times[dead_pid] = time.time()
                            logger.info(
                                f"Worker {dead_pid} can be restarted "
                                f"(attempt {self.restart_counts[dead_pid]}/{self.max_restart_attempts})"
                            )
                            recoverable = True
                        else:
                            logger.error(
                                f"Worker {dead_pid} exceeded max restart attempts"
                            )
                    
                    if not recoverable:
                        # 복구 불가능한 상황 - 시스템 종료
                        self.notify_main_process(
                            f"Workers {dead_workers} cannot be recovered. Shutting down system.",
                            critical=True
                        )
                        break
                    
                    consecutive_failures += 1
                    
                    # 연속 실패가 많으면 시스템 종료
                    if consecutive_failures >= 3:
                        self.notify_main_process(
                            "Too many consecutive worker failures. System unstable.",
                            critical=True
                        )
                        break
                else:
                    # 모든 워커가 정상이면 카운터 리셋
                    if consecutive_failures > 0:
                        logger.info("All workers recovered")
                    consecutive_failures = 0
                
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error("Unexpected error: {e}")
                time.sleep(self.check_interval)
        
        logger.info("Watchdog process shutting down")
    
    def stop(self):
        """감시 프로세스 정지"""
        self._running = False


def _watchdog_process_target(worker_pids: List[int],
                            check_interval: float,
                            max_restart_attempts: int,
                            config_path: str = None):
    """
    Watchdog 프로세스의 타겟 함수 (최상위 레벨 함수로 pickle 가능)
    """
    # 메인 프로세스와 동일한 로거 설정 사용
    if config_path:
        from utility.logger import setup_logger
        setup_logger(config_path)
    
    from loguru import logger
    
    watchdog = WorkerWatchdog(
        worker_pids=worker_pids,
        check_interval=check_interval,
        max_restart_attempts=max_restart_attempts
    )
    watchdog.run()


def create_watchdog_subprocess(worker_processes: List[multiprocessing.Process],
                              check_interval: float = 2.0,
                              max_restart_attempts: int = 3,
                              config_path: str = None) -> multiprocessing.Process:
    """
    워커 감시 프로세스를 생성하고 시작
    
    Args:
        worker_processes: 모니터링할 워커 프로세스 리스트
        check_interval: 확인 주기
        max_restart_attempts: 최대 재시작 시도 횟수
        config_path: 로거 설정을 위한 config 파일 경로
    
    Returns:
        시작된 watchdog 프로세스
    """
    worker_pids = [p.pid for p in worker_processes if p.pid is not None]
    
    watchdog_process = multiprocessing.Process(
        target=_watchdog_process_target,
        args=(worker_pids, check_interval, max_restart_attempts, config_path),
        name="WorkerWatchdog",
        daemon=False  # 메인 프로세스가 죽어도 정리 작업을 완료할 수 있도록
    )
    watchdog_process.start()
    
    return watchdog_process