document.addEventListener('DOMContentLoaded', () => {
  const token = localStorage.getItem('access_token');
  if (!token) {
      // 토큰이 없으면 로그인 페이지로 즉시 리디렉션
      window.location.href = '/login';
      return;
  }

  // --- DOM 요소 참조 ---
  const emailSpan = document.getElementById('currentUserEmail');
  const idSpan = document.getElementById('currentUserId');
  const isVerifiedSpan = document.getElementById('currentUserIsVerified');
  const isSuperuserSpan = document.getElementById('currentUserIsSuperuser');
  const userListSection = document.getElementById('user-list-section');
  const userListTable = document.getElementById('userListTable');
  const userListMessage = document.getElementById('userListMessage');
  const changePasswordForm = document.getElementById('changePasswordForm');
  const userListTableBody = document.getElementById('userListTableBody');
  const refreshUserListButton = document.getElementById('refreshUserListButton');
  const userListError = document.getElementById('userListError');
  const userActionMessage = document.getElementById('userActionMessage');

  let currentLoggedInUserId = null;

  /**
   * 현재 로그인된 사용자의 정보를 가져와 UI에 표시
   */
  async function fetchCurrentUserInfo() {
      try {
          const response = await authService.fetchWithAuth('/users/me');

          if (!response.ok) {
              if (response.status === 401) { // 토큰이 유효하지 않은 경우
                  localStorage.clear(); // 잘못된 토큰 삭제
                  window.location.href = '/login';
              }
              throw new Error('사용자 정보를 가져오는데 실패했습니다.');
          }

          const user = await response.json();
          currentLoggedInUserId = user.id;

          // UI 업데이트
          if (emailSpan) emailSpan.textContent = user.email;
          if (idSpan) idSpan.textContent = user.id;
          if (isVerifiedSpan) isVerifiedSpan.textContent = user.is_verified ? '예 (이메일 인증됨)' : '아니오';
          if (isSuperuserSpan) isSuperuserSpan.textContent = user.is_superuser ? '예 (관리자)' : '아니오';
          
          // 사용자가 슈퍼유저인 경우, 관리자 섹션을 표시
          if (user.is_superuser) {
              if (userListSection) userListSection.style.display = 'block';
              if (refreshUserListButton) {
                  refreshUserListButton.style.display = 'block';
                  refreshUserListButton.onclick = fetchUserList;
              }
              fetchUserList();
          }

      } catch (error) {
        if (error.message !== 'Unauthorized') {
            console.error('Error fetching current user info:', error);
            document.getElementById('currentUserInfo').innerHTML = `<p class="error-message">${error.message}</p>`;
        }
      }
  }

  /**
   * 비밀번호 변경 폼 제출을 처리
   */
  if (changePasswordForm) {
      changePasswordForm.addEventListener('submit', async (event) => {
          event.preventDefault();
          const newPassword = document.getElementById('newPassword').value;
          const confirmNewPassword = document.getElementById('confirmNewPassword').value;
          const messageDiv = document.getElementById('changePasswordMessage');
          messageDiv.textContent = '';
          messageDiv.className = '';

          if (newPassword !== confirmNewPassword) {
              messageDiv.textContent = '새 비밀번호가 일치하지 않습니다.';
              messageDiv.className = 'error-message';
              return;
          }
          if (newPassword.length < 6) {
              messageDiv.textContent = '비밀번호는 6자리 이상이어야 합니다.';
              messageDiv.className = 'error-message';
              return;
          }

          messageDiv.textContent = '비밀번호 변경 중...';
          try {
                const response = await authService.fetchWithAuth('/users/me/password', {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ new_password: newPassword })
                });

                if (response.ok) {
                    messageDiv.textContent = '비밀번호가 성공적으로 변경되었습니다. 다시 로그인해주세요.';
                    messageDiv.className = 'success-message';
                    changePasswordForm.reset();
                    localStorage.removeItem('access_token');
                    authService.logout();
                } else {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || '비밀번호 변경에 실패했습니다.');
                }
          } catch (error) {
              messageDiv.textContent = `오류: ${error.message}`;
              messageDiv.className = 'error-message';
          }
      });
  }
  
  /**
   * (관리자용) 백엔드에서 전체 사용자 목록을 가져와 테이블에 표시
   */
  async function fetchUserList() {
      if (!userListTableBody) return;
      if (userActionMessage) userActionMessage.textContent = '';
      if (userListError) userListError.style.display = 'none';
      userListTableBody.innerHTML = '<tr><td colspan="6">사용자 목록을 불러오는 중...</td></tr>';

      try {
          const response = await authService.fetchWithAuth('/users/');

          if (!response.ok) {
              const errorData = await response.json();
              throw new Error(errorData.detail || '사용자 목록을 가져오는데 실패했습니다.');
          }

          const users = await response.json();
          userListTableBody.innerHTML = ''; // 테이블 비우기

          if (users.length > 0) {
            userListTable.style.display = 'table';
            userListMessage.style.display = 'none';
          } else {
            userListTable.style.display = 'none';
            userListMessage.style.display = 'block';
            userListMessage.textContent = '등록된 사용자가 없습니다.';
            return;
          }

          users.forEach(user => {
              const row = userListTableBody.insertRow();
              const isSuperuser = user.is_superuser || (user.user_metadata && user.user_metadata.role === 'admin');
              const isVerified = user.is_verified || user.email_confirmed_at !== null;

              row.insertCell().textContent = user.email;
              row.insertCell().textContent = user.id;
              row.insertCell().textContent = isVerified ? '예' : '아니오';
              row.insertCell().textContent = isSuperuser ? '예' : '아니오';
              
              const actionCell = row.insertCell();
              if (user.id === currentLoggedInUserId) {
                  actionCell.textContent = '(현재 사용자)';
              } else {
                  const deleteButton = document.createElement('button');
                  deleteButton.textContent = '삭제';
                  deleteButton.className = 'delete-user-btn';
                  deleteButton.onclick = () => handleDeleteUser(user.id, user.email);
                  actionCell.appendChild(deleteButton);
              }
          });

      } catch (error) {
          console.error('Error fetching user list:', error);
          if (userListError) {
              userListError.textContent = error.message;
              userListError.style.display = 'block';
          }
      }
  }

  /**
   * (관리자용) 특정 사용자 삭제를 처리
   */
  async function handleDeleteUser(userId, userEmail) {
      if (!userActionMessage) return;
      userActionMessage.textContent = '';
      userActionMessage.className = '';

      if (confirm(`정말로 사용자 '${userEmail}' (ID: ${userId}) 계정을 삭제하시겠습니까?`)) {
          userActionMessage.textContent = `사용자 '${userEmail}' 삭제 중...`;
          try {
              const response = await fetch(`/users/${userId}`, {
                  method: 'DELETE',
              });

              if (response.ok) {
                  userActionMessage.textContent = `사용자 '${userEmail}'이(가) 성공적으로 삭제되었습니다.`;
                  userActionMessage.className = 'success-message';
                  fetchUserList(); // 삭제 후 목록 새로고침
              } else {
                  const errorData = await response.json();
                  throw new Error(errorData.detail || '계정 삭제에 실패했습니다.');
              }
          } catch (error) {
              userActionMessage.textContent = `오류: ${error.message}`;
              userActionMessage.className = 'error-message';
          }
      }
  }

  // 페이지 로드 시 현재 사용자 정보 가져오기 시작
  fetchCurrentUserInfo();
});