from fastapi import Request, HTTPException, status
from supabase import Client

from app.utility.request import get_manager_config 


def get_supabase_client(request: Request) -> Client:
    """
    app.state에 저장된 익명(anon) 키 Supabase 클라이언트를 반환하는 의존성 함수
    (이 함수를 만들려면 main.py lifespan에도 anon key 클라이언트 생성 로직이 필요합니다.)
    """
    try:
        # main.py lifespan에서 app.state.supabase_client = create_client(...) 를 추가해야 함
        client = request.app.state.supabase_client 
        if client is None:
            raise HTTPException(status_code=500, detail="Supabase client not initialized")
        return client
    except AttributeError:
        raise HTTPException(status_code=500, detail="Supabase client not found in app state")

def get_supabase_admin_client(request: Request) -> Client:
    """
    app.state에 저장된 어드민(service_role) Supabase 클라이언트를 반환하는 의존성 함수
    """
    try:
        client = request.app.state.supabase_admin_client
        if client is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Supabase admin client not initialized")
        return client
    except AttributeError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Supabase admin client not found in app state")
