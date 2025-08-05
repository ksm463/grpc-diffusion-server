// /web/static/js/_navbar.js

document.addEventListener('DOMContentLoaded', () => {
    checkLoginStatus();

    const logoutButton = document.getElementById('logoutButton');
    if (logoutButton) {
        logoutButton.addEventListener('click', handleLogout);
    }
});

/**
 * access_token이 있는지 확인하여 로그인/로그아웃 버튼의 표시 여부를 결정
 */
function checkLoginStatus() {
    const loginNavItem = document.getElementById('nav-login-item');
    const logoutNavItem = document.getElementById('nav-logout-item');
    const token = localStorage.getItem('access_token');

    if (token) {
        // 토큰이 있으면 '로그인' 버튼을 숨기고 '로그아웃' 버튼을 표시
        if (loginNavItem) loginNavItem.style.display = 'none';
        if (logoutNavItem) logoutNavItem.style.display = 'list-item';
    } else {
        // 토큰이 없으면 '로그인' 버튼을 표시하고 '로그아웃' 버튼을 숨김
        if (loginNavItem) loginNavItem.style.display = 'list-item';
        if (logoutNavItem) logoutNavItem.style.display = 'none';
    }
}

/**
 * 로그아웃 버튼 클릭 시 호출되는 함수
 */
async function handleLogout() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        alert('로그인 상태가 아닙니다.');
        window.location.href = '/login';
        return;
    }

    try {
        const response = await fetch('/auth/logout', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            console.error('Server logout failed:', await response.json());
        }

    } catch (error) {
        console.error('Error during logout request:', error);
    } finally {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');

        alert('성공적으로 로그아웃되었습니다.');
        checkLoginStatus();
        window.location.href = '/login';
    }
}