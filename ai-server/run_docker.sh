#!/bin/bash

port_num="2"
CONTAINER_NAME="ai-server"
NETWORK_NAME="diffusion-net"
IMAGE_NAME="grpc-server-image"
TAG="pytorch2405"

grpc_ai_path=$(pwd)

docker run \
    -it \
    -p 50051:50051 \
    -p ${port_num}5000:5000 \
    -p ${port_num}8888:8888 \
    --name ${CONTAINER_NAME} \
    --privileged \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v ${grpc_ai_path}:/grpc-ai-server \
    -v /etc/localtime:/etc/localtime:ro \
    -e DISPLAY=$DISPLAY \
    -e HOST_IP="$HOST_IP" \
    -e HOST_OS_VERSION="$HOST_OS_VERSION" \
    -e HOST_TIMEZONE="$HOST_TIMEZONE" \
    --shm-size 20g \
    --restart=always \
    -w /grpc-ai-server \
    ${IMAGE_NAME}:${TAG}

docker network connect ${NETWORK_NAME} ${CONTAINER_NAME}
