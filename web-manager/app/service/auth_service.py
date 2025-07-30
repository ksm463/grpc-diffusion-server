from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from supabase import Client
from gotrue.types import User 

from database.supabase import get_supabase_client
from utility.request import get_logger

# 토큰은 클라이언트가 'Authorization: Bearer <TOKEN>' 형태로 전송
# tokenUrl은 실제 로그인 엔드포인트 경로로 지정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    supabase: Client = Depends(get_supabase_client),
    logger = Depends(get_logger)
) -> User:
    """
    요청 헤더의 JWT를 검증하고 Supabase 사용자 정보를 반환합니다.
    """
    try:
        # set_session을 사용하지 않고, 토큰을 직접 get_user에 전달합니다.
        # 이 방법이 더 명시적이고 안정적입니다.
        user_response = supabase.auth.get_user(token)
        
        # user_response 객체나 user_response.user가 None일 수 있으므로 함께 확인합니다.
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user session or token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = user_response.user
        return user
        
    except Exception as e:
        # gotrue-py 라이브러리는 유효하지 않은 토큰에 대해 예외를 발생시킵니다.
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

# def get_authenticated_supabase_client(
#     token: str = Depends(oauth2_scheme),
#     supabase: Client = Depends(get_supabase_client)
# ) -> Client:
#     """
#     토큰으로 세션이 설정된 Supabase 클라이언트를 반환합니다.
#     """
#     supabase.auth.set_session(token, "")
#     return supabase

# # 슈퍼유저(Superuser)를 확인하는 의존성
# # Supabase에서는 보통 user_metadata에 역할을 저장하여 확인
# async def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
#     """
#     현재 사용자가 슈퍼유저인지 확인
#     Supabase의 user_metadata에 'role': 'admin'과 같이 저장되어 있다고 가정함
#     """
#     if "role" not in current_user.user_metadata or current_user.user_metadata["role"] != "admin":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="The user doesn't have enough privileges"
#         )
#     return current_user