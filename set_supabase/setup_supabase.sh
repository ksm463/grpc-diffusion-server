#!/bin/bash

set -e

# --- 1. NVM 및 Node.js 설치 확인 ---
echo "✅ 1. NVM 및 Node.js 환경 확인..."

export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    source "$NVM_DIR/nvm.sh"
else
    echo "오류: NVM이 설치되어 있지 않거나 경로를 찾을 수 없습니다."
    echo "NVM을 먼저 설치해주세요: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash"
    exit 1
fi

# Node.js LTS 버전이 설치되어 있지 않으면 설치
if ! nvm list | grep -q "lts"; then
    echo "Node.js LTS 버전이 설치되어 있지 않습니다. 설치를 시작합니다..."
    nvm install --lts
    nvm use --lts
else
    echo "Node.js LTS 버전이 이미 설치되어 있습니다."
    nvm use --lts
fi

# npx 명령어 확인
if ! command -v npx &> /dev/null; then
    echo "오류: npx 명령어를 찾을 수 없습니다. Node.js/npm 설치를 확인해주세요."
    exit 1
fi

echo "Node.js 환경 준비 완료. 현재 버전: $(node -v)"
echo "----------------------------------------"


# --- 2. Supabase 프로젝트 초기화 ---
echo "✅ 2. Supabase 프로젝트 초기화 확인..."

if [ ! -d "supabase" ]; then
    echo "'supabase' 디렉토리가 없습니다. 프로젝트를 초기화합니다..."
    npx supabase init
    echo "Supabase 프로젝트가 성공적으로 초기화되었습니다."
else
    echo "'supabase' 디렉토리가 이미 존재합니다. 초기화를 건너뜁니다."
fi

echo "----------------------------------------"


# --- 3. Supabase 실행 ---
echo "✅ 3. Supabase 실행..."

# 'docker ps' 명령어로 supabase 관련 컨테이너가 실행 중인지 확인
# 'supabase-db' 컨테이너를 기준으로 확인
if docker ps | grep -q "supabase-db"; then
    echo "Supabase 컨테이너가 이미 실행 중입니다."
else
    echo "Supabase 컨테이너를 시작합니다. 잠시 기다려주세요..."
    npx supabase start
fi

echo "모든 Supabase 설정이 완료되었습니다!"
echo "아래 정보를 docker-compose.yml 파일의 환경 변수로 사용하세요."
npx supabase status