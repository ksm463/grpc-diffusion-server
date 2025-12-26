// 즉시 실행 함수(IIFE)와 전역 객체를 사용해 코드를 캡슐화하고 충돌을 방지
(function(window) {
  'use strict';

  // 다른 스크립트에서 사용할 수 있도록 authService 객체를 window에 할당
  const authService = {};

  /**
   * 로컬 스토리지에서 access token을 가져옴
   * @returns {string|null} - 저장된 토큰 또는 null
   */
  authService.getToken = function() {
      return localStorage.getItem('access_token');
  };

  /**
   * 사용자가 인증되었는지 (토큰이 있는지) 확인
   * @returns {boolean} - 인증 여부
   */
  authService.isAuthenticated = function() {
      return !!this.getToken();
  };

  /**
   * 로그아웃 처리 토큰을 삭제하고 로그인 페이지로 리디렉션합
   */
  authService.logout = function() {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      console.info('로그아웃 되었습니다. 로그인 페이지로 이동합니다.');
      window.location.href = '/login';
  };

  /**
   * 인증 헤더를 포함하여 fetch API를 실행하는 래퍼(wrapper) 함수입니다.
   * 401 Unauthorized 응답을 받으면 자동으로 로그아웃 처리합니다.
   * @param {string} url - 요청할 URL
   * @param {object} [options={}] - fetch에 전달할 옵션
   * @returns {Promise<Response>} - fetch의 응답 Promise
   */
  authService.fetchWithAuth = async function(url, options = {}) {
      const token = this.getToken();
      if (!token) {
          console.error('인증 토큰이 없어 API를 요청할 수 없습니다.');
          this.logout();
          return Promise.reject(new Error('No authentication token found.'));
      }

      // 기본 헤더와 사용자 정의 헤더를 병합
      const headers = {
          ...options.headers,
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/json' // JSON 응답을 선호함을 명시
      };

      const response = await fetch(url, { ...options, headers });

      if (response.status === 401) {
          console.error('인증이 만료되었거나 유효하지 않습니다 (401).');
          this.logout();
          throw new Error('Unauthorized');
      }

      return response;
  };

  /**
   * 페이지 로드 시 인증 상태를 확인하고 비인증 시 리디렉션
   * 이 함수는 auth.js가 로드될 때 즉시 실행
   */
  function checkAuthenticationAndRedirect() {
      // 로그인, 회원가입 페이지에서는 이 검사를 수행하지 않도록 예외 처리
      const publicPaths = ['/login', '/create_account'];
      if (publicPaths.includes(window.location.pathname)) {
          return;
      }

      if (!authService.isAuthenticated()) {
          console.info('인증되지 않은 접근입니다. 로그인 페이지로 리디렉션합니다.');
          // logout 함수가 리디렉션을 처리하므로 호출만 하면 됨
          authService.logout();
      }
  }
  
  // 스크립트가 로드되자마자 인증 상태를 확인
  checkAuthenticationAndRedirect();

  // 전역 window 객체에 authService를 노출
  window.authService = authService;

})(window);