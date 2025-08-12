from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from supabase import Client
from gotrue.types import User 

from database.supabase import get_supabase_client
from utility.request import get_logger

# 토큰은 클라이언트가 'Authorization: Bearer <TOKEN>' 형태로 전송
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

async def get_current_user(
    request: Request,
    token_from_header: Optional[str] = Depends(oauth2_scheme),
    supabase: Client = Depends(get_supabase_client),
    logger = Depends(get_logger)
) -> User:
    """
    요청 헤더의 JWT를 검증하고 Supabase 사용자 정보를 반환
    """
    token = token_from_header or request.cookies.get("access_token")

    if not token:
        # 헤더에도, 쿠키에도 토큰이 없는 경우에만 인증 실패 처리
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid user session or token.")
        
        user = user_response.user
        return user
        
    except Exception as e:
        logger.warning(f"Failed to authenticate token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# 슈퍼유저(Superuser) 확인
async def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """
    현재 사용자가 슈퍼유저인지 확인
    """
    if not current_user.user_metadata or current_user.user_metadata.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
