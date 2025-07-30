from configparser import ConfigParser
from fastapi import Depends
from supabase import create_client, Client

from app.utility.request import get_manager_config 


def get_supabase_client(config: ConfigParser = Depends(get_manager_config)) -> Client:
    """
    설정 파일에서 정보를 읽어 Supabase 클라이언트를 반환하는 의존성 함수
    """
    supabase_url = config['SUPABASE']['URL']
    supabase_key = config['SUPABASE']['KEY']
    
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase URL and Key must be set in manager_config.ini")
        
    return create_client(supabase_url, supabase_key)

def get_supabase_admin_client(config: ConfigParser = Depends(get_manager_config)) -> Client:
    """
    설정 파일에서 정보를 읽어 Supabase 어드민 클라이언트를 반환하는 의존성 함수
    """
    supabase_url = config['SUPABASE']['URL']
    supabase_service_key = config['SUPABASE']['SERVICE_KEY']

    if not supabase_url or not supabase_service_key:
        raise ValueError("Supabase URL and Service Key must be set in manager_config.ini")
        
    return create_client(supabase_url, supabase_service_key)
