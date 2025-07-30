import uuid
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    """
    Supabase 사용자 정보를 클라이언트에게 응답하기 위한 스키마.
    필요한 필드만 정의합니다.
    """
    id: uuid.UUID
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    password: str | None = None
    data: dict | None = None

class UpdatePasswordRequest(BaseModel):
    # 보안을 위해 현재 비밀번호를 요구하려면 별도 로직이 필요
    new_password: str = Field(..., min_length=6)