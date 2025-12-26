const loginForm = document.getElementById('login-form');
const errorMessageDiv = document.getElementById('error-message');

loginForm.addEventListener('submit', async function(event) {
    event.preventDefault();
    errorMessageDiv.textContent = '';

    // FormData 대신 각 input에서 직접 값을 가져옴
    const email = loginForm.elements.email.value;
    const password = loginForm.elements.password.value;

    try {
        // 이전에 정의한 Supabase 로그인 엔드포인트를 호출
        const response = await fetch('/auth/db/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email,
                password: password,
            }),
        });

        const responseData = await response.json();

        if (response.ok) { // 로그인 성공 시 (상태 코드 200-299)
            // 서버로부터 받은 access_token과 refresh_token을 브라우저의 localStorage에 저장
            localStorage.setItem('access_token', responseData.access_token);
            localStorage.setItem('refresh_token', responseData.refresh_token);
            
            console.log('Login successful. Token stored.');
            window.location.href = '/studio';

        } else { // 로그인 실패 시
            // 서버에서 보낸 에러 메시지를 표시
            const messageToDisplay = responseData.detail || '아이디 또는 비밀번호가 잘못되었습니다.';
            console.error('Login failed:', response.status, responseData);
            errorMessageDiv.textContent = messageToDisplay;
        }

    } catch (error) {
        // 네트워크 오류 등
        console.error('Error during login request:', error);
        errorMessageDiv.textContent = '로그인 중 오류가 발생했습니다. 네트워크 연결을 확인해 주세요.';
    }
});