from fastapi import APIRouter, Depends, Query
from typing import List
from datetime import datetime, timezone, timedelta

from database.schemas import ImageCreationRequest
from service.image_requester import images_paginated
from service.auth_service import get_current_user
from utility.request import get_manager_config, get_server_config, get_logger


image_router = APIRouter()


@image_router.post("/generate")
async def generate_image(
    request_data: ImageCreationRequest,
    user: dict = Depends(get_current_user),
    manager_config=Depends(get_manager_config),
    server_config=Depends(get_server_config),
    logger=Depends(get_logger)
):
    """
    클라이언트로부터 프롬프트와 설정값을 받아 이미지를 생성하는 프로세스
    """
    # 1. 클라이언트로부터 받은 데이터 확인 
    user_id = user.get("id")
    logger.info(f"User '{user_id}' send request for image generation: {request_data.model_dump_json(indent=2)}")

    # 3. (향후 구현) gRPC 클라이언트를 호출하여 AI 서버에 작업 요청
    #    gRPC 요청에 필요한 데이터를 request_data에서 가져와 사용합니다.
    #    response = await grpc_client.generate_image(
    #        prompt=request_data.prompt,
    #        ...
    #    )

    # 4. (향후 구현) gRPC 응답을 받아 Supabase에 저장

    # 5. 임시로 성공 응답을 반환하는 예시입니다.
    #    실제로는 Supabase에 업로드된 이미지 URL을 반환해야 합니다.
    temp_image_url = f"https://via.placeholder.com/{request_data.width}x{request_data.height}.png?text=Generated+Image+for+{request_data.prompt[:20]}"
    
    return {
        "image_url": temp_image_url,
        "used_seed": request_data.seed if request_data.seed != -1 else 12345, # 예시 시드
        "message": "Image generation started successfully."
    }

@image_router.get("/gallery/api/my-images", response_model=List[dict])
async def get_my_images(
    user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100)
):
    """
    (임시) 샘플 이미지 목록을 반환합니다.
    향후에는 현재 로그인된 사용자가 생성한 이미지 목록을 Supabase에서 가져옵니다.
    """
    images = await images_paginated(page=page, limit=limit)
    return images