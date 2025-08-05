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