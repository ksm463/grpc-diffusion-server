#!/bin/bash

# 디렉토리의 절대 경로 추출
SCRIPT_DIR=$(dirname "$(readlink -f "$0" || realpath "$0")")

# 스크립트 디렉토리 내의 redis.conf 파일 경로를 구성합
CONF_FILE="$SCRIPT_DIR/redis.conf"

# redis.conf 파일이 존재하는지 확인
if [ ! -f "$CONF_FILE" ]; then
  echo "Error: redis.conf not found in the script directory ($SCRIPT_DIR)"
  exit 1
fi

# 찾은 설정 파일을 사용하여 redis-server를 실행
echo "Starting redis-server with config: $CONF_FILE"
redis-server "$CONF_FILE"

echo "Redis server process started."
