#!/bin/bash

port_num="2"
CONTAINER_NAME="web-manager"
NETWORK_NAME="diffusion-net"
IMAGE_NAME="web-manager"
TAG="0.1"

fastapi_path=$(pwd)

HOST_IP=$(hostname -I | awk '{print $1}')
HOST_OS_VERSION=$(cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '"' || echo "N/A")
HOST_TIMEZONE=$(timedatectl status | grep 'Time zone' | awk '{print $3 " (" $4 $5}' | sed 's/)//g; s/(//g' || cat /etc/timezone || echo "N/A")

echo "--- Host System Information (to be passed to container) ---"
echo "Host IP: $HOST_IP"
echo "Host OS Version: $HOST_OS_VERSION"
echo "Host Timezone: $HOST_TIMEZONE"
echo "----------------------------------------------------------"


docker run \
    -d \
    -p ${port_num}7000:7000 \
    -p ${port_num}8000:8000 \
    --name ${CONTAINER_NAME} \
    --network ${NETWORK_NAME} \
    --privileged \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v ${fastapi_path}:/web-manager \
    -e DISPLAY=$DISPLAY \
    -e HOST_IP="$HOST_IP" \
    -e HOST_OS_VERSION="$HOST_OS_VERSION" \
    -e HOST_TIMEZONE="$HOST_TIMEZONE" \
    -e SUPABASE_URL="http://${HOST_IP}:54321" \
    -e SUPABASE_KEY="" \
    -e SUPABASE_SERVICE_KEY="" \
    --shm-size 20g \
    --restart=always \
    -w /web-manager \
    ${IMAGE_NAME}:${TAG} \
    tail -f /dev/null

