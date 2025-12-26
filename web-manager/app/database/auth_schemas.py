import uuid
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="사용자 이메일 주소")
    password: str = Field(..., min_length=6, description="비밀번호 (최소 6자)")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "securepassword123"
                }
            ]
        }

class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="사용자 이메일 주소")
    password: str = Field(..., description="비밀번호")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "securepassword123"
                }
            ]
        }

class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    password: str | None = None
    data: dict | None = None

class UpdatePasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6)


class AuthResponse(BaseModel):
    """
    로그인 성공 시 반환되는 JWT 토큰 응답
    """
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "access_token": "<supabase_jwt_access_token>",
                    "refresh_token": "<supabase_jwt_refresh_token>",
                    "token_type": "bearer"
                }
            ]
        }


class MessageResponse(BaseModel):
    """
    일반적인 메시지 응답
    """
    message: str = Field(..., description="Response message")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "message": "User created successfully. Please check your email to confirm."
                }
            ]
        }


class UserInfoResponse(BaseModel):
    """
    현재 사용자 정보 응답
    """
    email: str = Field(..., description="사용자 이메일")
    id: str = Field(..., description="사용자 UUID")
    is_verified: bool = Field(..., description="이메일 인증 여부")
    is_superuser: bool = Field(..., description="관리자 여부")
    user_metadata: dict = Field(default={}, description="사용자 메타데이터")
    created_at: str = Field(..., description="계정 생성 일시")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "email": "user@example.com",
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "is_verified": True,
                    "is_superuser": False,
                    "user_metadata": {"role": "user"},
                    "created_at": "2025-12-26T10:00:00.000000+00:00"
                }
            ]
        }


class AdminUserItem(BaseModel):
    """
    관리자 사용자 목록의 개별 사용자 정보
    """
    id: str = Field(..., description="사용자 UUID")
    email: str = Field(..., description="사용자 이메일")
    phone: str = Field(default="", description="사용자 전화번호")
    created_at: str = Field(..., description="계정 생성 일시")
    updated_at: str = Field(..., description="계정 수정 일시")
    confirmed_at: str | None = Field(None, description="계정 인증 일시")
    email_confirmed_at: str | None = Field(None, description="이메일 인증 일시")
    phone_confirmed_at: str | None = Field(None, description="전화번호 인증 일시")
    last_sign_in_at: str | None = Field(None, description="마지막 로그인 일시")
    user_metadata: dict = Field(default_factory=dict, description="사용자 메타데이터")
    app_metadata: dict = Field(default_factory=dict, description="앱 메타데이터")
    aud: str = Field(..., description="Audience")
    role: str = Field(..., description="사용자 역할")
    is_anonymous: bool = Field(default=False, description="익명 사용자 여부")
    confirmation_sent_at: str | None = Field(None, description="인증 이메일 발송 일시")
    recovery_sent_at: str | None = Field(None, description="복구 이메일 발송 일시")
    email_change_sent_at: str | None = Field(None, description="이메일 변경 요청 일시")
    new_email: str | None = Field(None, description="새 이메일 (변경 요청 시)")
    new_phone: str | None = Field(None, description="새 전화번호 (변경 요청 시)")
    invited_at: str | None = Field(None, description="초대 일시")
    action_link: str | None = Field(None, description="액션 링크")
    identities: list | None = Field(None, description="연결된 인증 정보")
    factors: list | None = Field(None, description="다중 인증 요소")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "id": "423ecf9f-96eb-4d79-af05-019ee113366c",
                    "email": "user@example.com",
                    "phone": "",
                    "created_at": "2025-08-23T10:08:20.358054Z",
                    "updated_at": "2025-12-26T07:50:28.148283Z",
                    "confirmed_at": "2025-08-23T10:08:20.378366Z",
                    "email_confirmed_at": "2025-08-23T10:08:20.378366Z",
                    "phone_confirmed_at": None,
                    "last_sign_in_at": "2025-12-26T07:50:28.143064Z",
                    "user_metadata": {
                        "email": "user@example.com",
                        "email_verified": True,
                        "phone_verified": False,
                        "role": "admin"
                    },
                    "app_metadata": {
                        "provider": "email",
                        "providers": ["email"]
                    },
                    "aud": "authenticated",
                    "role": "authenticated",
                    "is_anonymous": False,
                    "confirmation_sent_at": None,
                    "recovery_sent_at": None,
                    "email_change_sent_at": None,
                    "new_email": None,
                    "new_phone": None,
                    "invited_at": None,
                    "action_link": None,
                    "identities": None,
                    "factors": None
                }
            ]
        }
