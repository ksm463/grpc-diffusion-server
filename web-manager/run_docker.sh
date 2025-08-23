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
    -e SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0" \
    -e SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU" \
    --shm-size 20g \
    --restart=always \
    -w /web-manager \
    ${IMAGE_NAME}:${TAG} \
    tail -f /dev/null

