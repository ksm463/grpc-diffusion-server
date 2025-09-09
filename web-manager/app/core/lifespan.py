from contextlib import asynccontextmanager
from fastapi import FastAPI
from pathlib import Path
from supabase import create_client, Client
import os

from app.core.config import manager_config, server_config
from utility.logger import setup_logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 앱의 라이프스팬 이벤트를 관리합니다. (시작/종료)
    """
    # 로거 설정
    log_path = manager_config['ENV']['LOG_PATH']
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    logger = setup_logger(log_path)
    logger.info("Logging server started")
    
    # Supabase 클라이언트 생성
    logger.info("Creating Supabase clients...")
    supabase_url = os.getenv('SUPABASE_URL', manager_config['SUPABASE']['URL'])
    supabase_key = os.getenv('SUPABASE_KEY', manager_config['SUPABASE']['KEY'])
    supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY', manager_config['SUPABASE']['SERVICE_KEY'])
    
    
    if not all([supabase_url, supabase_key, supabase_service_key]):
        error_msg = "Supabase URL, Key, and Service Key must be set in manager_config.ini"
        logger.error(error_msg)
        raise ValueError(error_msg)

    supabase_client: Client = create_client(supabase_url, supabase_key)
    supabase_admin_client: Client = create_client(supabase_url, supabase_service_key)
    logger.info("Supabase clients created successfully.")

    # app.state에 필요한 객체들 저장
    app.state.logger = logger
    app.state.manager_config = manager_config
    app.state.server_config = server_config
    app.state.supabase_client = supabase_client
    app.state.supabase_admin_client = supabase_admin_client
    
    yield
    
    # === 애플리케이션 종료 시 실행될 코드 ===
    logger.info("Logging server stopped")