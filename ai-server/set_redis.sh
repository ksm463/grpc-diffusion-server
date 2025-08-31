#!/bin/bash

CONTAINER_NAME="redis-server"
NETWORK_NAME="diffusion-net"
IMAGE_NAME="redis"
TAG="6.0.16"
REDIS_PORT="6379"

# 기존에 실행 중인 동일 이름의 컨테이너가 있다면 중지하고 삭제
if [ $(docker ps -q -f name=^/${CONTAINER_NAME}$) ]; then
    echo "Stopping and removing existing container: ${CONTAINER_NAME}"
    docker stop ${CONTAINER_NAME} > /dev/null
    docker rm ${CONTAINER_NAME} > /dev/null
fi

# diffusion-net 네트워크가 없으면 생성
if ! docker network ls | grep -q ${NETWORK_NAME}; then
    echo "Creating network: ${NETWORK_NAME}"
    docker network create ${NETWORK_NAME}
fi

echo "Pulling Redis image: ${IMAGE_NAME}:${TAG}"
docker pull ${IMAGE_NAME}:${TAG} > /dev/null

echo "Running Redis container..."
docker run \
    -d \
    -p ${REDIS_PORT}:${REDIS_PORT} \
    --name ${CONTAINER_NAME} \
    --network ${NETWORK_NAME} \
    --restart=always \
    ${IMAGE_NAME}:${TAG}

echo "Redis container '${CONTAINER_NAME}' is running on port ${REDIS_PORT}."