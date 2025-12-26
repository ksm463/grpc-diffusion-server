import uuid
import grpc
from typing import List
from fastapi import HTTPException

import sys
import os

# stub파일을 가져오기 위해 경로를 /web-manager/app로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
protos_path = os.path.join(parent_dir, 'protos')
sys.path.append(protos_path)

import diffusion_processing_pb2
import diffusion_processing_pb2_grpc

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
) -> ImageGenerationResponse:
    """
    이미지 생성 요청의 비즈니스 로직 처리
    1. gRPC를 통해 AI 서버에 이미지 생성을 요청
    2. 생성된 이미지 바이너리를 Supabase Storage에 직접 업로드
    3. 작업 내역을 Supabase DB에 기록
    4. 클라이언트에 최종 결과 반환
    """
    user_id = user.id
    logger.info(f"User '{user_id}' sent request for image generation: {request_data.model_dump_json(indent=2)}")

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
    logger.info(f"Prepared AI server request (request_id: {request_id})")

    # 1. gRPC 클라이언트를 호출하여 AI 서버에 작업 요청
    ai_server_address = manager_config['ADDRESS'].get('SERVER_IP_ADDRESS')
    if not ai_server_address:
        logger.error("AI Server IP address is not configured.")
        raise HTTPException(status_code=500, detail="AI server is not configured.")

    try:
        async with grpc.aio.insecure_channel(ai_server_address) as channel:
            stub = diffusion_processing_pb2_grpc.ImageGeneratorStub(channel)
            grpc_request = diffusion_processing_pb2.GenerationRequest(
                request_id=str(ai_server_request.request_id),
                prompt=ai_server_request.prompt,
                guidance_scale=ai_server_request.guidance_scale,
                num_inference_steps=ai_server_request.num_inference_steps,
                width=ai_server_request.width,
                height=ai_server_request.height,
                seed=ai_server_request.seed
            )
            logger.info(f"Sending request to AI server at {ai_server_address}...")
            grpc_response = await stub.GenerateImage(grpc_request)
            logger.info(f"Received response from AI server for request_id: {grpc_response.request_id}")

    except grpc.aio.AioRpcError as e:
        logger.error(f"gRPC call failed for request_id '{request_id}': {e.details()}")
        raise HTTPException(status_code=503, detail=f"AI server is unavailable: {e.details()}")

    if grpc_response.status == diffusion_processing_pb2.GenerationResponse.Status.FAILURE:
        logger.error(f"AI server failed to generate image for request_id '{request_id}': {grpc_response.error_message}")
        raise HTTPException(status_code=500, detail=f"AI server failed: {grpc_response.error_message}")

    # 2. 성공 시 이미지 데이터를 Supabase Storage에 업로드
    image_data = grpc_response.image_data
    final_seed = grpc_response.used_seed
    
    # Storage 내 파일 경로를 유저별로 구분하여 생성
    image_filename = f"{request_id}.jpg"
    storage_path = f"{user_id}/{image_filename}"
    bucket_name = "generated-images"  # 사전 준비 사항에서 생성한 버킷 이름

    try:
        # Supabase Storage에 파일 업로드
        db.storage.from_(bucket_name).upload(
            file=image_data,
            path=storage_path,
            file_options={"content-type": "image/jpeg"}
        )
        logger.info(f"Successfully uploaded image to Supabase Storage: {storage_path}")

        # 업로드된 파일의 Public URL 가져오기
        response = db.storage.from_(bucket_name).get_public_url(storage_path)
        image_url = response

    except Exception as e:
        logger.error(f"Failed to upload image to Supabase Storage: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image to storage.")

    # 3. Supabase 'images' 테이블에 데이터 삽입
    image_record_data = ImageRecordCreate(
        user_id=user_id,
        image_url=image_url,
        prompt=request_data.prompt,
        guidance_scale=request_data.guidance_scale,
        num_inference_steps=request_data.num_inference_steps,
        width=request_data.width,
        height=request_data.height,
        seed=final_seed
    )
    
    try:
        db.from_("images").insert(image_record_data.model_dump(mode='json')).execute()
        logger.info(f"Successfully inserted image record for user '{user_id}' into Supabase.")
    except Exception as e:
        logger.error(f"Failed to insert image record into Supabase: {e}")
        # 참고: 이 경우 이미지는 Storage에 업로드되었지만 DB 기록은 실패한 상태가 됩니다.
        # 필요 시 업로드된 파일을 삭제하는 보상 트랜잭션(transaction) 로직을 추가할 수 있습니다.

    # 4. 클라이언트에 최종 응답 반환
    logger.info(f"Returning generated image URL: {image_url}")

    return ImageGenerationResponse(
        image_url=image_url,
        used_seed=final_seed,
        message="Image generated and uploaded successfully."
    )
