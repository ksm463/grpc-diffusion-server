from loguru import logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from loguru import Logger

def setup_logger(log_path: str) -> "Logger":
    """
    loguru 로거(logger)를 설정
    """
    logger.remove()

    # 콘솔 출력 로거
    # logger.add(
    #     sys.stdout,
    #     level="INFO",
    #     format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> [<level>{level.name}</level>] <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    # )

    # 파일 출력 로거
    logger.add(
        log_path,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} [{level.name}] {file.name}:{line} - {message}",
        rotation="30 MB",  # 30MB 이후 새 파일 생성
        retention=5,  # 최대 5개의 로그 파일 유지
        encoding='utf-8',
        enqueue=True,      # 비동기 및 다중 프로세스 환경 로깅
        backtrace=True,    # 예외 발생 시 스택 추적
        diagnose=True      # 예외 발생 시 상세 정보 추가
    )

    return logger
