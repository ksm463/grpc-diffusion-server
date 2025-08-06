document.addEventListener('DOMContentLoaded', function() {
    fetchMyImages();
});

async function fetchMyImages() {
    const galleryGrid = document.getElementById('gallery-grid');
    const placeholder = document.getElementById('gallery-placeholder');

    try {
        // auth.js의 fetchWithAuth 함수를 사용하거나 직접 fetch를 구현
        const response = await fetch('/gallery/api/my-images', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });

        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        if (!response.ok) {
            throw new Error('서버에서 데이터를 불러오는 데 실패했습니다.');
        }

        const images = await response.json();

        if (images.length === 0) {
            placeholder.textContent = '아직 생성한 이미지가 없습니다.';
        } else {
            placeholder.style.display = 'none'; // 플레이스홀더 숨기기
            images.forEach(image => {
                const card = createImageCard(image);
                galleryGrid.innerHTML += card;
            });
        }

    } catch (error) {
        console.error("Error fetching images:", error);
        placeholder.textContent = '이미지를 불러오는 중 오류가 발생했습니다.';
        placeholder.style.color = '#dc3545';
    }
}

function createImageCard(image) {
    const creationDate = new Date(image.created_at).toLocaleString('ko-KR');

    return `
        <div class="gallery-card">
            <img src="${image.image_url}" alt="${image.prompt || 'Generated Image'}" loading="lazy">
            <div class="gallery-card-info">
                <p class="gallery-prompt" title="${image.prompt || ''}">${image.prompt || '프롬프트 없음'}</p>
                <p class="gallery-date">${creationDate}</p>
            </div>
        </div>
    `;
}