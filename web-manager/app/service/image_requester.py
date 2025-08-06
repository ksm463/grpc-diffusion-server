from typing import List
from datetime import datetime, timezone, timedelta

async def images_paginated(page: int, limit: int) -> List[dict]:
    """
    (서비스 계층) 샘플 이미지 데이터를 생성하고 페이지네이션을 적용하여 반환합니다.
    """
    all_sample_images = []
    base_time = datetime.now(timezone.utc)
    for i in range(1, 5):
        all_sample_images.append({
            "image_url": f"/preview/sd_sample_{i}.jpg",
            "prompt": f"AI로 생성된 샘플 이미지 {i}입니다.",
            "created_at": (base_time - timedelta(minutes=i*5)).isoformat(),
        })

    # 페이지네이션 계산
    start_index = (page - 1) * limit
    end_index = start_index + limit
    
    paginated_images = all_sample_images[start_index:end_index]
    
    return paginated_images