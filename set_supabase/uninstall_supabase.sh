#!/bin/bash

set -e

echo "========================================="
echo "  Supabase 정리 스크립트"
echo "========================================="
echo ""

# --- 1. NVM 환경 설정 ---
echo "✅ 1. NVM 및 Node.js 환경 확인..."

export NVM_DIR="$HOME/.nvm"

# NVM이 설치되어 있는지 확인
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    echo "⚠️  경고: NVM이 설치되어 있지 않습니다."
    echo "Supabase CLI(npx supabase)를 사용하려면 NVM이 필요합니다."
    echo ""
    echo "대신 Docker 명령어로 직접 정리하시겠습니까? (y/n)"
    read -r answer
    if [ "$answer" = "y" ]; then
        USE_DOCKER_DIRECT=true
    else
        echo "정리를 취소했습니다."
        exit 1
    fi
else
    # NVM 환경 불러오기
    source "$NVM_DIR/nvm.sh"

    # Node.js LTS 사용
    if nvm list | grep -q "lts"; then
        nvm use --lts > /dev/null 2>&1
        echo "Node.js 환경 준비 완료. 현재 버전: $(node -v)"
    else
        echo "⚠️  경고: Node.js LTS 버전이 설치되어 있지 않습니다."
        USE_DOCKER_DIRECT=true
    fi
fi

echo "----------------------------------------"
echo ""

# --- 2. 현재 Supabase 리소스 확인 ---
echo "✅ 2. Supabase 리소스 확인..."
echo ""

SUPABASE_CONTAINERS=$(docker ps -a --filter "name=supabase" --format "{{.Names}}" | wc -l)
SUPABASE_VOLUMES=$(docker volume ls --filter "name=supabase" --format "{{.Name}}" | wc -l)
SUPABASE_IMAGES=$(docker images | grep supabase | wc -l)

echo "발견된 Supabase 리소스:"
echo "  - 컨테이너: $SUPABASE_CONTAINERS 개"
echo "  - 볼륨: $SUPABASE_VOLUMES 개"
echo "  - 이미지: $SUPABASE_IMAGES 개"
echo ""

if [ "$SUPABASE_CONTAINERS" -eq 0 ] && [ "$SUPABASE_VOLUMES" -eq 0 ] && [ "$SUPABASE_IMAGES" -eq 0 ]; then
    echo "정리할 Supabase 리소스가 없습니다."
    exit 0
fi

if [ "$SUPABASE_CONTAINERS" -gt 0 ]; then
    echo "컨테이너 목록:"
    docker ps -a --filter "name=supabase" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
fi

echo "----------------------------------------"
echo ""

# --- 3. 정리 옵션 선택 ---
echo "✅ 3. 정리 옵션 선택"
echo ""
echo "다음 중 원하는 작업을 선택하세요:"
echo "  1) 컨테이너만 중지 및 제거 (볼륨/이미지 유지)"
echo "  2) 컨테이너 + 볼륨 삭제 (이미지 유지) ⚠️  데이터 삭제됨"
echo "  3) 컨테이너 + 볼륨 + 이미지 완전 삭제 ⚠️  모든 데이터/이미지 삭제됨"
echo "  4) 취소"
echo ""
read -p "선택 (1-4): " choice

case $choice in
    1)
        REMOVE_VOLUMES=false
        REMOVE_IMAGES=false
        echo "➡️  컨테이너만 제거합니다."
        ;;
    2)
        REMOVE_VOLUMES=true
        REMOVE_IMAGES=false
        echo "⚠️  컨테이너와 볼륨을 삭제합니다. (데이터 손실)"
        ;;
    3)
        REMOVE_VOLUMES=true
        REMOVE_IMAGES=true
        echo "⚠️  컨테이너, 볼륨, 이미지를 모두 삭제합니다. (완전 제거)"
        ;;
    4)
        echo "정리를 취소했습니다."
        exit 0
        ;;
    *)
        echo "잘못된 선택입니다. 종료합니다."
        exit 1
        ;;
esac

echo ""
echo "----------------------------------------"
echo ""

# --- 4. 최종 확인 ---
echo "⚠️  경고: 이 작업은 되돌릴 수 없습니다!"
echo ""
read -p "정말로 진행하시겠습니까? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "정리를 취소했습니다."
    exit 0
fi

echo ""
echo "----------------------------------------"
echo ""

# --- 5. Supabase 컨테이너 중지 및 제거 ---
if [ "$SUPABASE_CONTAINERS" -gt 0 ]; then
    echo "✅ 4. Supabase 컨테이너 중지 중..."
    echo ""

    if [ "$USE_DOCKER_DIRECT" = true ]; then
        # Docker 명령어로 직접 중지
        echo "Docker 명령어로 컨테이너를 중지합니다..."
        docker ps --filter "name=supabase" --format "{{.Names}}" | xargs -r docker stop
        echo "✅ 컨테이너 중지 완료"
    else
        # npx supabase stop 사용
        echo "npx supabase stop 실행 중..."
        if [ "$REMOVE_VOLUMES" = true ]; then
            npx supabase stop --no-backup
        else
            npx supabase stop
        fi
        echo "✅ Supabase 중지 완료"
    fi

    echo ""
    echo "----------------------------------------"
    echo ""

    # --- 6. 컨테이너 제거 ---
    echo "✅ 5. Supabase 컨테이너 제거 중..."
    echo ""

    STOPPED_CONTAINERS=$(docker ps -a --filter "name=supabase" --format "{{.Names}}" | wc -l)

    if [ "$STOPPED_CONTAINERS" -gt 0 ]; then
        docker ps -a --filter "name=supabase" --format "{{.Names}}" | xargs -r docker rm
        echo "✅ $STOPPED_CONTAINERS 개의 컨테이너 제거 완료"
    else
        echo "제거할 컨테이너가 없습니다."
    fi

    echo ""
    echo "----------------------------------------"
    echo ""
else
    echo "✅ 4. 컨테이너가 없으므로 중지/제거 단계를 건너뜁니다."
    echo ""
    echo "----------------------------------------"
    echo ""
fi

# --- 6. 볼륨 삭제 (옵션) ---
if [ "$REMOVE_VOLUMES" = true ]; then
    echo "✅ 5. Supabase 볼륨 삭제 중..."
    echo ""

    SUPABASE_VOLUMES=$(docker volume ls --filter "name=supabase" --format "{{.Name}}" | wc -l)

    if [ "$SUPABASE_VOLUMES" -gt 0 ]; then
        echo "발견된 Supabase 볼륨:"
        docker volume ls --filter "name=supabase" --format "{{.Name}}"
        echo ""
        docker volume ls --filter "name=supabase" --format "{{.Name}}" | xargs -r docker volume rm
        echo "✅ $SUPABASE_VOLUMES 개의 볼륨 삭제 완료"
    else
        echo "삭제할 볼륨이 없습니다."
    fi

    echo ""
    echo "----------------------------------------"
    echo ""
fi

# --- 7. 이미지 삭제 (옵션) ---
if [ "$REMOVE_IMAGES" = true ]; then
    echo "✅ 6. Supabase 이미지 삭제 중..."
    echo ""

    SUPABASE_IMAGES=$(docker images | grep supabase | wc -l)

    if [ "$SUPABASE_IMAGES" -gt 0 ]; then
        echo "발견된 Supabase 이미지 ($SUPABASE_IMAGES 개):"
        docker images | grep supabase | head -10
        if [ "$SUPABASE_IMAGES" -gt 10 ]; then
            echo "... 그 외 $(($SUPABASE_IMAGES - 10)) 개 더 있음"
        fi
        echo ""

        # 이미지 삭제 (force 옵션 사용)
        docker images | grep supabase | awk '{print $3}' | xargs -r docker rmi -f

        REMAINING=$(docker images | grep supabase | wc -l)
        if [ "$REMAINING" -eq 0 ]; then
            echo "✅ $SUPABASE_IMAGES 개의 이미지 삭제 완료"
        else
            echo "⚠️  $((SUPABASE_IMAGES - REMAINING)) 개 삭제됨, $REMAINING 개 삭제 실패 (사용 중일 수 있음)"
        fi
    else
        echo "삭제할 이미지가 없습니다."
    fi

    echo ""
    echo "----------------------------------------"
    echo ""
fi

# --- 9. 완료 ---
echo "========================================="
echo "  ✅ Supabase 정리 완료!"
echo "========================================="
echo ""
echo "정리 요약:"
echo "  - 컨테이너: 제거됨"
if [ "$REMOVE_VOLUMES" = true ]; then
    echo "  - 볼륨: 삭제됨 ⚠️"
else
    echo "  - 볼륨: 유지됨"
fi
if [ "$REMOVE_IMAGES" = true ]; then
    echo "  - 이미지: 삭제됨 ⚠️"
else
    echo "  - 이미지: 유지됨"
fi
echo ""

# --- 10. 남은 Supabase 리소스 확인 ---
echo "남은 Supabase 리소스:"
echo ""
REMAINING_CONTAINERS=$(docker ps -a --filter "name=supabase" --format "{{.Names}}" | wc -l)
REMAINING_VOLUMES=$(docker volume ls --filter "name=supabase" --format "{{.Name}}" | wc -l)
REMAINING_IMAGES=$(docker images | grep supabase | wc -l)

echo "  - 컨테이너: $REMAINING_CONTAINERS 개"
echo "  - 볼륨: $REMAINING_VOLUMES 개"
echo "  - 이미지: $REMAINING_IMAGES 개"
echo ""

if [ "$REMAINING_CONTAINERS" -eq 0 ] && [ "$REMAINING_VOLUMES" -eq 0 ] && [ "$REMAINING_IMAGES" -eq 0 ]; then
    echo "✅ 모든 Supabase 리소스가 성공적으로 제거되었습니다!"
fi

echo "========================================="
