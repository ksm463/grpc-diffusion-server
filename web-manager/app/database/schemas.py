import uuid
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
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


class ImageCreationRequest(BaseModel):
    """
    이미지 생성을 위한 요청 바디(Request Body) 모델
    """
    prompt: str = Field(
        ...,
        title="Image Generation Prompt",
        description="이미지 생성을 위한 텍스트 프롬프트입니다.",
        min_length=1 # 최소 1글자 이상
    )
    guidance_scale: float = Field(
        7.0, # 기본값
        title="Guidance Scale",
        description="생성될 이미지가 프롬프트를 얼마나 따를지 결정하는 값입니다.",
        ge=1.0, # 최소값
        le=20.0 # 최대값
    )
    num_inference_steps: int = Field(
        28,
        title="Number of Inference Steps",
        description="이미지 생성 시 추론을 반복하는 횟수입니다.",
        ge=10,
        le=50
    )
    width: int = Field(1024, title="Image Width", ge=512, le=1536)
    height: int = Field(1024, title="Image Height", ge=512, le=1536)
    seed: Optional[int] = Field(
        -1, # JS에서 null로 보낸 경우
        title="Seed",
        description="이미지 생성을 위한 시드 값. -1일 경우 랜덤으로 처리합니다."
    )

    # /docs 용 예시
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "prompt": "A photorealistic image of an astronaut riding a horse",
                    "guidance_scale": 7.5,
                    "num_inference_steps": 30,
                    "width": 1024,
                    "height": 1024,
                    "seed": 123456789
                }
            ]
        }
