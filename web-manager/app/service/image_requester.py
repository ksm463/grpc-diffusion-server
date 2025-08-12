import uuid
from typing import List

from supabase import Client
from gotrue.types import User as SupabaseUser
from database.image_schemas import (
    ImageCreationRequest, 
    AIServerRequest,
    ImageGenerationResponse,
    ImageRecordCreate,
    ImageRecord
)


async def images_paginated(
    user: SupabaseUser, 
    db: Client, 
    page: int, 
    limit: int,
    logger
) -> List[ImageRecord]:
    """
    로그인된 사용자의 이미지 목록을 Supabase에서 가져와 웹에 전달
    """
    try:
        start_index = (page - 1) * limit
        end_index = start_index + limit - 1

        # Supabase 쿼리 실행
        response = db.from_("images").select("*") \
            .eq('user_id', user.id) \
            .order('created_at', desc=True) \
            .range(start_index, end_index) \
            .execute()

        logger.info(f"Fetched {len(response.data)} images for user '{user.id}' from Supabase.")
        
        # Pydantic 모델로 데이터 변환 (타입 안정성 확보)
        # response.data는 딕셔너리의 리스트입니다.
        images = [ImageRecord.model_validate(item) for item in response.data]
        return images

    except Exception as e:
        logger.error(f"Failed to fetch images from Supabase for user '{user.id}': {e}")
        return []


async def image_generation_request(
    request_data: ImageCreationRequest,
    user: SupabaseUser,
    db: Client,
    manager_config: dict,
    server_config: dict,
    logger
) -> dict:
    """
    이미지 생성 요청의 비즈니스 로직 처리
    """
    # 1. 클라이언트로부터 받은 데이터 확인
    user_id = user.id
    logger.info(f"User '{user_id}' sent request for image generation: {request_data.model_dump_json(indent=2)}")

    # 2. AI 서버에 보낼 요청 데이터 생성
    request_id = str(uuid.uuid4())
    ai_server_request = AIServerRequest(
        request_id=request_id,
        prompt=request_data.prompt,
        guidance_scale=request_data.guidance_scale,
        num_inference_steps=request_data.num_inference_steps,
        width=request_data.width,
        height=request_data.height,
        seed=request_data.seed
    )
    logger.info(f"Prepared AI server request (request_id: {request_id}): {ai_server_request}")

    # 3. (향후 구현) gRPC 클라이언트를 호출하여 AI 서버에 작업 요청
    #    예: response = await grpc_client.generate_image(**ai_server_request)

    # 4. 임시 결과 이미지 
    temp_image_url = "/preview/sd_sample_3.jpg"
    final_seed = request_data.seed if request_data.seed != -1 else 12345
    
    # 5. Supabase에 저장할 데이터 준비
    image_record_data = ImageRecordCreate(
        user_id=user_id,
        image_url=temp_image_url,
        prompt=request_data.prompt,
        guidance_scale=request_data.guidance_scale,
        num_inference_steps=request_data.num_inference_steps,
        width=request_data.width,
        height=request_data.height,
        seed=final_seed
    )
    logger.info(f"Prepared data for Supabase: {image_record_data.model_dump_json(indent=2)}")

    # 6. Supabase 'images' 테이블에 데이터 삽입
    try:
        db.from_("images").insert(image_record_data.model_dump(mode='json')).execute()
        logger.info(f"Successfully inserted image record for user '{user_id}' into Supabase.")
    except Exception as e:
        logger.error(f"Failed to insert image record into Supabase: {e}")
    
    # 7. 클라이언트에 최종 응답 반환
    logger.info(f"Returning temporary sample image: {temp_image_url}")

    return ImageGenerationResponse(
        image_url=temp_image_url,
        used_seed=request_data.seed if request_data.seed != -1 else 12345,
        message="Image generation started successfully."
    )
