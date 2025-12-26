from fastapi import APIRouter, Depends, Query
from typing import List
from supabase import Client
from gotrue.types import User as SupabaseUser

from database.image_schemas import ImageCreationRequest, ImageGenerationResponse, ImageRecord
from database.supabase import get_supabase_admin_client
from service.image_requester import images_paginated, image_generation_request
from service.auth_service import get_current_user
from utility.request import get_manager_config, get_server_config, get_logger


image_router = APIRouter()


@image_router.post(
    "/api/studio/generate",
    response_model=ImageGenerationResponse,
    tags=["image"]
)
async def generate_image(
    request_data: ImageCreationRequest,
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase_admin_client),
    manager_config=Depends(get_manager_config),
    server_config=Depends(get_server_config),
    logger=Depends(get_logger)
):
    """
    클라이언트로부터 프롬프트와 설정값을 받아 이미지를 생성하는 프로세스
    """
    response = await image_generation_request(
        request_data=request_data,
        user=user,
        db=db,
        manager_config=manager_config,
        server_config=server_config,
        logger=logger
    )
    
    return response

@image_router.get(
    "/api/gallery/my-images",
    response_model=List[ImageRecord],
    tags=["image"]
)
async def get_my_images(
    user: SupabaseUser = Depends(get_current_user),
    db: Client = Depends(get_supabase_admin_client),
    logger=Depends(get_logger),
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100)
):
    """
    현재 로그인된 사용자가 생성한 이미지 목록을 Supabase에서 가져옵니다.
    """
    images = await images_paginated(
        user=user, 
        db=db, 
        logger=logger,
        page=page, 
        limit=limit
    )
    return images
