// --- 전역 변수 및 요소 참조 ---
const appContainer = document.getElementById('app');
const pageContents = document.querySelectorAll('.page-content');
const copyButton = document.getElementById('copyProtoButton');
const token = localStorage.getItem('access_token');

// --- 인증 오류 처리 함수 ---
function handleAuthError(response) {
  if (response.status === 401) {
      console.error('인증 실패(401). 로그인 페이지로 리디렉션합니다.');
      localStorage.clear(); // 만료되거나 잘못된 토큰 삭제
      window.location.href = '/login';
      return true;
  }
  return false;
}

// --- gRPC 정보 가져오는 함수 ---
async function fetchGrpcPortInfo() {
  const grpcInfoDiv = document.getElementById('grpcPortInfo');
  if (!grpcInfoDiv) return;
  grpcInfoDiv.innerHTML = 'Loading... <span class="loader"></span>';

  try {
    const response = await fetch('/api/info/grpc_info', {
      headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!response.ok) {
    if (handleAuthError(response)) return;
    throw new Error(`HTTP error! status: ${response.status}`);
  }
    const data = await response.json();
    grpcInfoDiv.innerHTML = `gRPC Port: <span>${data.grpc_port || 'Not available'}</span>`;
  } catch (error) {
    console.error('Failed to fetch gRPC info:', error);
    grpcInfoDiv.textContent = 'Failed to load gRPC port information.';
    grpcInfoDiv.style.color = '#dc3545';
    grpcInfoDiv.style.fontWeight = 'bold';
  }
}

// --- PROTO 파일 조회 함수 ---
async function fetchProtoFileContent() {
    const contentDisplay = document.getElementById('protoFileContent');
    const downloadButton = document.getElementById('downloadProtoButton');
    const viewButton = document.getElementById('viewProtoButton');

    if (copyButton) {
        copyButton.style.display = 'none';
        copyButton.classList.remove('copied');
        copyButton.textContent = '📋';
    }
    contentDisplay.textContent = 'Loading PROTO content...';
    contentDisplay.classList.remove('error-message');
    downloadButton.disabled = true;
    viewButton.disabled = true;

    try {
      const response = await fetch('/api/info/proto', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) {
          if (handleAuthError(response)) return;
          let errorDetail = `HTTP error! status: ${response.status}`;
          try {
              const errorData = await response.json();
              if (errorData.detail) {
                  errorDetail = `Error: ${errorData.detail} (Status: ${response.status})`;
              }
          } catch (e) { /* 응답이 JSON이 아닐 수 있음 */ }
          throw new Error(errorDetail);
      }
      const protoContent = await response.text();
      contentDisplay.textContent = protoContent;
      downloadButton.disabled = false;
      if (copyButton && protoContent && protoContent !== "조회 버튼을 눌러 PROTO 파일 내용을 불러오세요." && !protoContent.startsWith("Loading") && !protoContent.startsWith("Failed")) {
          copyButton.style.display = 'inline-block';
      }
    } catch (error) {
        console.error('Failed to fetch PROTO content:', error);
        contentDisplay.textContent = `Failed to load PROTO file: ${error.message}`;
        contentDisplay.classList.add('error-message');
        downloadButton.disabled = true;
        if (copyButton) {
            copyButton.style.display = 'none';
        }
    } finally {
        viewButton.disabled = false;
    }
}

// --- 이벤트 리스너 설정 함수 ---
function addMainPageEventListeners() {
  const downloadButton = document.getElementById('downloadProtoButton');
  const viewButton = document.getElementById('viewProtoButton');
  const copyButton = document.getElementById('copyProtoButton');
  const contentDisplay = document.getElementById('protoFileContent');

  if (viewButton) {
      viewButton.addEventListener('click', fetchProtoFileContent);
  }

  if (downloadButton) {
    downloadButton.addEventListener('click', () => {
      if (!contentDisplay) return;
      const content = contentDisplay.textContent;
      if (!downloadButton.disabled && content && !content.startsWith('Loading') && !content.startsWith('Failed') && content !== "조회 버튼을 눌러 PROTO 파일 내용을 불러오세요.") {
        const filename = "server_proto.proto";
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      } else {
        alert("No valid content to download.");
      }
    });
  }

  if (copyButton) {
      copyButton.addEventListener('click', async () => {
        if (!contentDisplay) return;
          const textToCopy = document.getElementById('protoFileContent').textContent;
          if (textToCopy && !textToCopy.startsWith('Loading') && !textToCopy.startsWith('Failed') && textToCopy !== "조회 버튼을 눌러 PROTO 파일 내용을 불러오세요.") {
              try {
                  await navigator.clipboard.writeText(textToCopy);
                  copyButton.textContent = '✅';
                  copyButton.classList.add('copied');
                  setTimeout(() => {
                      copyButton.textContent = '📋';
                      copyButton.classList.remove('copied');
                  }, 1500);
              } catch (err) {
                  console.error('클립보드 복사 실패:', err);
                  alert('클립보드 복사에 실패했습니다. 브라우저 설정을 확인하거나 수동으로 복사해주세요.');
              }
          } else {
              alert('복사할 내용이 없습니다.');
          }
      });
  }
}

// 페이지 초기 로드
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('main-page-content')) {
    addMainPageEventListeners();
    fetchGrpcPortInfo();
  }
});