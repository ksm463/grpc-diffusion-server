from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import List
from supabase import Client
from gotrue.errors import AuthApiError

from database.schemas import UserCreate, UserLogin, UserRead, UpdatePasswordRequest
from database.supabase import get_supabase_client, get_supabase_admin_client
from service.auth_service import get_current_user, get_current_superuser
from utility.request import get_logger

from gotrue.types import User as SupabaseUser 

account_router = APIRouter()

# --- 회원가입 ---
@account_router.post("/auth/register", status_code=status.HTTP_201_CREATED, tags=["auth"])
async def signup(
    user_credentials: UserCreate,
    supabase: Client = Depends(get_supabase_client),
    logger=Depends(get_logger)
):
    """
    새로운 사용자 등록
    """
    try:
        # Supabase에 사용자 생성을 요청
        # Supabase 설정에서 이메일 인증이 활성화된 경우, 확인 메일이 발송
        sign_up_data = {"email": user_credentials.email, "password": user_credentials.password}
        response = supabase.auth.sign_up(sign_up_data)
        logger.info(f"User registration initiated for {response.user.email}")
        return {"message": "User created successfully. Please check your email to confirm."}
    except Exception as e:
        logger.error(f"Error during user registration: {e}", exc_info=True)
        # Supabase API는 오류 발생 시 gotrue.errors.AuthApiError 예외를 발생
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# --- 로그인 ---
@account_router.post("/auth/db/login", tags=["auth"])
async def login(
    form_data: UserLogin,
    supabase: Client = Depends(get_supabase_client),
    logger=Depends(get_logger)
):
    """
    사용자 로그인을 처리하고 JWT를 반환
    """
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": form_data.email, "password": form_data.password}
        )
        logger.info(f"User {response.user.email} logged in successfully.")
        # 클라이언트는 access_token과 refresh_token을 저장
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

# --- 로그아웃 API ---
@account_router.post("/auth/logout", tags=["auth"], status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: SupabaseUser = Depends(get_current_user),
    supabase_admin: Client = Depends(get_supabase_admin_client),
    logger=Depends(get_logger)
):
    try:
        supabase_admin.auth.admin.sign_out(uid=user.id)
        logger.info(f"All sessions for user {user.email} (ID: {user.id}) have been invalidated.")
    except Exception as e:
        logger.error(f"Error during sign out for user {user.email}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Supabase sign out failed: {e}"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- 보호된 라우트 ---
@account_router.get("/authenticated-route")
async def authenticated_route(
    user: SupabaseUser = Depends(get_current_user),
    logger=Depends(get_logger)
):
    logger.info(f"User '{user.email}' (ID: {user.id}) accessed /authenticated-route.")
    return {"message": f"Hello {user.email}!"}

# --- 현재 사용자 정보 ---
@account_router.get("/users/me", tags=["users"])
async def get_my_info(
    user: SupabaseUser = Depends(get_current_user),
    logger=Depends(get_logger)
):
    """
    현재 로그인된 사용자의 정보를 반환
    """
    logger.info(f"Fetching info for user {user.email} (ID: {user.id}).")
    is_superuser = user.user_metadata.get("role") == "admin"
    is_verified = user.email_confirmed_at is not None

    return {
        "email": user.email,
        "id": user.id,
        "is_active": True,  # Supabase에서는 별도의 is_active 플래그가 없으므로 항상 True로 간주
        "is_verified": is_verified,
        "is_superuser": is_superuser,
        "user_metadata": user.user_metadata,
        "created_at": user.created_at,
    }

# --- 비밀번호 변경 API ---
@account_router.patch("/users/me/password", status_code=status.HTTP_204_NO_CONTENT, tags=["users"])
async def update_my_password(
    password_data: UpdatePasswordRequest,
    user: SupabaseUser = Depends(get_current_user),
    supabase_admin: Client = Depends(get_supabase_admin_client),
    logger=Depends(get_logger)
):
    try:
        supabase_admin.auth.admin.update_user_by_id(
            uid=user.id,
            attributes={"password": password_data.new_password}
        )
        logger.info(f"Password updated successfully for user {user.email} (ID: {user.id}).")
    except Exception as e:
        logger.error(f"Failed to update password for user {user.email}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- 전체 사용자 목록 (관리자 전용) ---
@account_router.get("/users/", response_model=List[UserRead], tags=["auth"])
async def list_all_users(
    admin_user: SupabaseUser = Depends(get_current_superuser),
    supabase_admin: Client = Depends(get_supabase_admin_client),
    logger=Depends(get_logger)
):
    """
    관리자 계정으로 모든 사용자 목록을 조회
    """
    logger.info(f"Admin user '{admin_user.email}' requested to list all users.")
    try:
        response = supabase_admin.auth.admin.list_users()
        return response.users
    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve users list.")

# --- (관리자용) 사용자 삭제 API ---
@account_router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["admin"])
async def delete_user_by_admin(
    user_id: str,
    admin_user: SupabaseUser = Depends(get_current_superuser),
    supabase_admin: Client = Depends(get_supabase_admin_client),
    logger=Depends(get_logger)
):
    """
    관리자가 특정 사용자를 ID로 삭제
    """
    if str(admin_user.id) == user_id:
        logger.warning(f"Admin user {admin_user.email} attempted to delete their own account.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin cannot delete their own account this way."
        )
    logger.info(f"Admin user {admin_user.email} is attempting to delete user ID: {user_id}.")
    try:
        supabase_admin.auth.admin.delete_user(user_id)
        logger.info(f"Successfully deleted user ID: {user_id} by admin {admin_user.email}.")
    except AuthApiError as e:
        logger.error(f"Failed to delete user ID {user_id}: {e.message}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
