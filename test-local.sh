#!/bin/bash
# test-local.sh - 로컬 테스트 스크립트 (간소화)

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧪 로컬 Docker 테스트${NC}"
echo ""

# 테스트할 서비스
if [ -z "$1" ]; then
    SERVICES=("ai-server" "web-manager")
else
    SERVICES=("$1")
fi

for SERVICE in "${SERVICES[@]}"; do
    echo ""
    echo "========================================"
    echo -e "${BLUE}Testing: $SERVICE${NC}"
    echo "========================================"
    
    # 1. 빌드
    echo -e "${YELLOW}📦 Building...${NC}"
    if docker build --target test -t ${SERVICE}:test ./${SERVICE}; then
        echo -e "${GREEN}✅ Build successful${NC}"
    else
        echo -e "${RED}❌ Build failed${NC}"
        exit 1
    fi
    
    # 2. 테스트 실행
    echo -e "${YELLOW}🧪 Running test_basic.py...${NC}"
    
    if [ "$SERVICE" == "ai-server" ]; then
        docker run --rm ${SERVICE}:test \
            bash -c "source .venv/bin/activate && pytest tests/test_basic.py -v"
    else
        docker run --rm ${SERVICE}:test \
            uv run pytest tests/test_basic.py -v
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Test passed${NC}"
    else
        echo -e "${RED}❌ Test failed${NC}"
        exit 1
    fi
done

echo ""
echo "========================================"
echo -e "${GREEN}🎉 All tests passed!${NC}"
echo "========================================"