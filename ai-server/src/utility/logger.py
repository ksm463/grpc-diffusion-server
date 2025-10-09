import sys
import configparser
from pathlib import Path
from loguru import logger

# 한 번만 설정되도록 플래그 사용
_is_logger_configured = False

def setup_logger(config_path: str):
    """설정 파일을 읽어 loguru 로거를 설정"""
    global _is_logger_configured
    if _is_logger_configured:
        return

    config = configparser.ConfigParser()
    config.read(config_path)

    log_dir = config['LOG']['LOG_FILE_PATH']
    log_name = config['LOG']['LOG_FILE_NAME']
    log_level = config['LOG']['LOG_LEVEL']
    log_rotation = config['LOG']['LOG_ROTATION']
    log_retention = int(config['LOG']['LOG_RETENTION'])
    log_encoding = config['LOG']['LOG_ENCODING']
    
    # 파일 경로 생성
    debug_log_path = str(Path(log_dir) / f"{log_name}_debug.log")
    info_log_path = str(Path(log_dir) / f"{log_name}_info.log")

    # 기존 설정을 모두 제거하고 새로 추가
    logger.remove()

    # 파일 로깅 설정
    logger.add(
        debug_log_path,
        level=log_level.upper(),
        rotation=log_rotation,
        retention=log_retention,
        enqueue=True,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {process.name}:{process.id} | {name}:{function}:{line} - {message}",
        encoding=log_encoding,
        backtrace=True,
        diagnose=True
    )

    # 2. INFO 레벨 이상을 기록하는 파일 로거
    logger.add(
        info_log_path,
        level="INFO",
        rotation=log_rotation,
        retention=log_retention,
        enqueue=True,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {process.name}:{process.id} | {name}:{function}:{line} - {message}",
        encoding=log_encoding,
        backtrace=True,
        diagnose=True
    )

    # 콘솔 로깅 설정 (INFO 레벨 이상)
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{process.name}:{process.id}</cyan> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    _is_logger_configured = True
    logger.info("Logger has been configured.")
