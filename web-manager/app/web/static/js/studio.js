document.addEventListener('DOMContentLoaded', () => {

    // 1. 필요한 HTML 요소들을 변수에 할당
    const promptInput = document.getElementById('prompt-input');
    const generateButton = document.getElementById('generate-button');
    const advancedSettings = {
        guidanceScale: document.getElementById('guidance-scale'),
        inferenceSteps: document.getElementById('inference-steps'),
        width: document.getElementById('width'),
        height: document.getElementById('height'),
        seedInput: document.getElementById('seed-input'),
        randomSeedButton: document.getElementById('random-seed-button')
    };
    const resultWrapper = document.getElementById('result-image-wrapper');

    // 슬라이더 값 표시를 위한 span 요소들
    const sliderValueSpans = {
        guidanceScale: document.getElementById('guidance-scale-value'),
        inferenceSteps: document.getElementById('inference-steps-value'),
        width: document.getElementById('width-value'),
        height: document.getElementById('height-value')
    };

    // --- 이벤트 리스너 설정 ---

    // '이미지 생성' 버튼 클릭 시 handleGenerateImage 함수 실행
    // ✅ 중복된 이벤트 리스너를 제거하고 하나만 남깁니다.
    generateButton.addEventListener('click', handleGenerateImage);

    // '랜덤 시드' 버튼 클릭 시
    advancedSettings.randomSeedButton.addEventListener('click', () => {
        // -1 또는 1과 2^53-1 사이의 매우 큰 랜덤 정수를 생성하여 시드 입력창에 설정
        advancedSettings.seedInput.value = Math.floor(Math.random() * Number.MAX_SAFE_INTEGER) + 1;
    });

    // 모든 슬라이더의 값이 변경될 때마다 화면에 표시되는 숫자도 업데이트
    Object.keys(sliderValueSpans).forEach(key => {
        const slider = advancedSettings[key]; // 수정: 불필요한 문자열 처리 제거
        if (slider) {
            // 초기 값 설정
            sliderValueSpans[key].textContent = slider.value;
            slider.addEventListener('input', (event) => {
                sliderValueSpans[key].textContent = event.target.value;
            });
        }
    });

    /**
     * '이미지 생성' 버튼을 눌렀을 때 실행되는 메인 함수
     */
    async function handleGenerateImage() {
        // 프롬프트가 비어있으면 경고창을 띄우고 함수를 종료
        if (!promptInput.value.trim()) {
            alert('프롬프트를 입력해주세요.');
            promptInput.focus();
            return;
        }

        // UI를 로딩 상태로 변경
        setLoadingState(true);

        // API 서버로 보낼 데이터 객체 생성
        const payload = {
            prompt: promptInput.value,
            guidance_scale: parseFloat(advancedSettings.guidanceScale.value),
            num_inference_steps: parseInt(advancedSettings.inferenceSteps.value, 10),
            width: parseInt(advancedSettings.width.value, 10),
            height: parseInt(advancedSettings.height.value, 10),
            seed: advancedSettings.seedInput.value ? parseInt(advancedSettings.seedInput.value, 10) : -1
        };

        try {
            const response = await authService.fetchWithAuth('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            // 응답이 성공적이지 않으면 에러 처리
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: '서버 응답 오류' }));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            displayResultImage(data.image_url);

        } catch (error) {
            if (error.message !== 'Unauthorized') {
                console.error('Error:', error);
                displayError(error.message);
            }
        } finally {
            // 성공/실패 여부와 관계없이 UI를 다시 활성 상태로 변경
            setLoadingState(false);
        }
    }

    /**
     * 로딩 상태에 따라 UI를 제어하는 함수
     * @param {boolean} isLoading - 로딩 중인지 여부
     */
    function setLoadingState(isLoading) {
        if (isLoading) {
            generateButton.disabled = true;
            generateButton.textContent = '생성 중...';
            resultWrapper.innerHTML = '<p>이미지를 생성하고 있습니다. 잠시만 기다려주세요...</p>';
        } else {
            generateButton.disabled = false;
            generateButton.textContent = '이미지 생성 (Generate)';
        }
    }

    /**
     * ✅ 이미지 URL을 받아 화면에 표시하는 함수
     * @param {string} imageUrl - 화면에 표시할 이미지의 URL
     */
    function displayResultImage(imageUrl) {
        resultWrapper.innerHTML = ''; // 이전 내용 삭제
        const img = document.createElement('img');
        img.src = imageUrl;
        img.alt = 'Generated Image';
        resultWrapper.appendChild(img);
    }

    /**
     * 에러 메시지를 화면에 표시하는 함수
     * @param {string} message - 표시할 에러 메시지
     */
    function displayError(message) {
        resultWrapper.innerHTML = `<p style="color: red;">오류가 발생했습니다: ${message}</p>`;
    }
});