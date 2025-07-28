from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import List
from supabase import Client
from gotrue.errors import AuthApiError

from core.supabase import get_supabase_client, get_supabase_admin_client
from service.auth_service import get_current_user, get_current_superuser
from database.schemas import UserCreate, UserLogin, UserRead 
from utility.request import get_logger

from gotrue.types import User as SupabaseUser 

account_router = APIRouter()

# --- 1. 회원가입 ---
@account_router.post("/auth/register", status_code=status.HTTP_201_CREATED, tags=["auth"])
async def signup(
    user_credentials: UserCreate,
    supabase: Client = Depends(get_supabase_client),
    logger=Depends(get_logger)
):
    """
    새로운 사용자를 등록합니다. Supabase의 `sign_up`을 호출합니다.
    """
    try:
        # Supabase에 사용자 생성을 요청합니다.
        # Supabase 설정에서 이메일 인증이 활성화된 경우, 확인 메일이 발송됩니다.
        sign_up_data = {"email": user_credentials.email, "password": user_credentials.password}
        response = supabase.auth.sign_up(sign_up_data)
        
        logger.info(f"User registration initiated for {response.user.email}")
        return {"message": "User created successfully. Please check your email to confirm."}

    except Exception as e:
        logger.error(f"Error during user registration: {e}", exc_info=True)
        # Supabase API는 오류 발생 시 gotrue.errors.AuthApiError 예외를 발생시킵니다.
        # 더 구체적인 예외 처리가 가능합니다.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --- 2. 로그인 ---
@account_router.post("/auth/db/login", tags=["auth"]) # 기존 경로 유지
async def login(
    form_data: UserLogin,
    supabase: Client = Depends(get_supabase_client),
    logger=Depends(get_logger)
):
    """
    사용자 로그인을 처리하고 JWT를 반환합니다.
    """
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": form_data.email, "password": form_data.password}
        )
        logger.info(f"User {response.user.email} logged in successfully.")
        # 클라이언트는 이 access_token과 refresh_token을 저장해야 합니다.
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": "bearer"
        }
    except Exception as e:
        logger.error(f"Error during login: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

# --- 3. 보호된 라우트 ---
@account_router.get("/authenticated-route")
async def authenticated_route(
    user: SupabaseUser = Depends(get_current_user), # 새로 만든 의존성 사용
    logger=Depends(get_logger)
):
    logger.info(f"User '{user.email}' (ID: {user.id}) accessed /authenticated-route.")
    return {"message": f"Hello {user.email}!"}


# --- 4. 전체 사용자 목록 (관리자 전용) ---
@account_router.get("/users/", response_model=List[UserRead], tags=["auth"])
async def list_all_users(
    admin_user: SupabaseUser = Depends(get_current_superuser), # 관리자 확인 의존성
    supabase_admin: Client = Depends(get_supabase_admin_client), # Admin 클라이언트 주입
    logger=Depends(get_logger)
):
    """
    관리자만 모든 사용자 목록을 조회할 수 있습니다.
    service_role 키를 사용하는 admin 클라이언트가 필요합니다.
    """
    logger.info(f"Admin user '{admin_user.email}' requested to list all users.")
    try:
        response = supabase_admin.auth.admin.list_users()
        return response.users
    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve users list.")
        
# 참고: 비밀번호 재설정, 사용자 정보 수정/삭제 등도 모두 Supabase 클라이언트의
# `reset_password_for_email`, `update_user`, `admin.delete_user` 등의 메서드로 구현합니다.

# --- 5. 로그아웃 API ---
@account_router.post("/auth/logout", tags=["auth"], status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: SupabaseUser = Depends(get_current_user), # 현재 로그인된 사용자인지 확인
    supabase: Client = Depends(get_supabase_client)
):
    """
    사용자 로그아웃을 처리하고 Supabase 세션을 무효화합니다.
    """
    try:
        # get_current_user 토큰으로 로그아웃 진행
        token = user.token         
        supabase.auth.sign_out(token) 

    except AuthApiError as e:
        # Supabase에서 오류가 발생한 경우
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Supabase sign out failed: {e.message}"
        )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)
