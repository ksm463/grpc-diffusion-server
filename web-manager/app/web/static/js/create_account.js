document.addEventListener('DOMContentLoaded', () => {
  const createAccountForm = document.getElementById('createAccountForm');
  // ID가 'email'로 변경된 입력 필드를 선택
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  const confirmPasswordInput = document.getElementById('confirmPassword');
  const messageDiv = document.getElementById('createAccountMessage');
  const createAccountButton = document.getElementById('createAccountButton');

  if (createAccountForm) {
      createAccountForm.addEventListener('submit', async (event) => {
          event.preventDefault();
          messageDiv.style.display = 'none';
          messageDiv.className = 'message-area';

          const email = emailInput.value;
          const password = passwordInput.value;
          const confirmPassword = confirmPasswordInput.value;

          if (password !== confirmPassword) {
              messageDiv.textContent = '비밀번호가 일치하지 않습니다.';
              messageDiv.classList.add('error');
              messageDiv.style.display = 'block';
              return;
          }
          
          createAccountButton.disabled = true;
          messageDiv.textContent = '계정 생성 중...';
          messageDiv.classList.remove('success', 'error');
          messageDiv.style.display = 'block';

          try {
              // Supabase 회원가입 엔드포인트('/auth/register')를 호출
              const response = await fetch('/auth/register', {
                  method: 'POST',
                  headers: {
                      'Content-Type': 'application/json',
                  },
                  // Body를 UserCreate 스키마에 맞게 email과 password만 전송
                  body: JSON.stringify({
                      email: email,
                      password: password,
                  }),
              });

              const responseData = await response.json();

              if (response.ok) {
                  // 성공 시, 백엔드에서 보낸 메시지를 표시
                  messageDiv.textContent = responseData.message || '계정이 성공적으로 생성되었습니다. 이메일을 확인해 주세요.';
                  messageDiv.classList.add('success');
                  createAccountForm.reset(); // 성공 후 폼 초기화
              } else {
                  // 실패 시, 백엔드에서 보낸 에러 메시지를 표시
                  const errorMessage = responseData.detail || '계정 생성에 실패했습니다.';
                  messageDiv.textContent = errorMessage;
                  messageDiv.classList.add('error');
              }
          } catch (error) {
              console.error('계정 생성 중 네트워크 또는 기타 오류:', error);
              messageDiv.textContent = '계정 생성 중 오류가 발생했습니다. 네트워크 연결을 확인해 주세요.';
              messageDiv.classList.add('error');
          } finally {
              messageDiv.style.display = 'block';
              createAccountButton.disabled = false;
          }
      });
  }
});