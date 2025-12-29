import uuid
import enum
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ImageCreationRequest(BaseModel):
    """
    이미지 생성을 위한 요청 바디(Request Body) 모델
    """
    prompt: str = Field(
        ...,
        title="Image Generation Prompt",
        description="이미지 생성을 위한 텍스트 프롬프트",
        min_length=1 # 최소 1글자 이상
    )
    guidance_scale: float = Field(
        7.0, # 기본값
        title="Guidance Scale",
        description="생성될 이미지가 프롬프트를 얼마나 따를지 결정하는 값",
        ge=1.0, # 최소값
        le=20.0 # 최대값
    )
    num_inference_steps: int = Field(
        28,
        title="Number of Inference Steps",
        description="이미지 생성 시 추론을 반복하는 횟수",
        ge=10,
        le=50
    )
    width: int = Field(1024, title="Image Width", ge=512, le=1536)
    height: int = Field(1024, title="Image Height", ge=512, le=1536)
    seed: Optional[int] = Field(
        -1, # JS에서 null로 보낸 경우
        title="Seed",
        description="이미지 생성을 위한 시드 값. -1일 경우 랜덤으로 처리"
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

class AIServerRequest(BaseModel):
    """
    AI 생성 서버에 작업을 요청하기 위한 데이터 모델
    """
    request_id: uuid.UUID
    prompt: str
    guidance_scale: float
    num_inference_steps: int
    width: int
    height: int
    seed: int

class GenerationStatus(str, enum.Enum):
    """
    AI 서버의 이미지 생성 작업 상태를 나타내는 Enum
    """
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class AIServerResponse(BaseModel):
    """
    AI 생성 서버의 작업 완료 후 반환되는 응답 모델
    """
    request_id: uuid.UUID = Field(
        ...,
        description="원본 요청을 식별하기 위한 고유 ID"
    )
    status: GenerationStatus = Field(
        ...,
        description="생성 작업의 성공/실패 여부"
    )
    # used_seed는 성공/실패 여부와 관계없이 사용된 값을 알아야 할 수 있으므로 필수로 유지
    used_seed: int = Field(
        ...,
        description="실제 이미지 생성에 사용된 시드 값"
    )
    image_data: Optional[bytes] = Field(
        default=None,
        description="생성 성공 시 이미지의 원시 바이너리 데이터 (uint8 배열)"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="생성 실패 시 에러 메시지"
    )

class ImageRecordCreate(BaseModel):
    """
    Supabase 'images' 테이블에 레코드를 생성하기 위한 모델
    """
    user_id: uuid.UUID
    image_url: str
    prompt: str
    guidance_scale: float
    num_inference_steps: int
    width: int
    height: int
    seed: int


class ImageRecord(ImageRecordCreate):
    """
    DB에서 'images' 레코드를 조회한 후 사용할 전체 데이터 모델
    """
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "examples": [
                {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "image_url": "https://your-project.supabase.co/storage/v1/object/public/generated-images/user-uuid/image-uuid.png",
                    "prompt": "A photorealistic image of an astronaut riding a horse",
                    "guidance_scale": 7.5,
                    "num_inference_steps": 28,
                    "width": 1024,
                    "height": 1024,
                    "seed": 42,
                    "id": "660e8400-e29b-41d4-a716-446655440001",
                    "created_at": "2025-12-26T16:30:00.000000+00:00"
                }
            ]
        }

class ImageGenerationResponse(BaseModel):
    """
    이미지 생성 요청에 대한 최종 응답 모델
    """
    image_url: str = Field(..., description="Supabase Storage에 업로드된 이미지 URL")
    used_seed: int = Field(..., description="실제로 사용된 시드 값")
    message: str = Field(..., description="처리 결과 메시지")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "image_url": "https://your-project.supabase.co/storage/v1/object/public/generated-images/user-uuid/image-uuid.png",
                    "used_seed": 42,
                    "message": "Image generated and uploaded successfully."
                }
            ]
        }