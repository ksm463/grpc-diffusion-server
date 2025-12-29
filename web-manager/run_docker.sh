#!/bin/bash

# Load environment variables from .env file if it exists
if [ -f "../.env" ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' ../.env | xargs)
else
    echo "Warning: .env file not found in parent directory"
fi

port_num="${PORT_NUM:-2}"
CONTAINER_NAME="web-manager"
NETWORK_NAME="diffusion-net"
IMAGE_NAME="${WEB_MANAGER_IMAGE_NAME:-web-manager}"
TAG="${WEB_MANAGER_IMAGE_TAG:-0.1}"

fastapi_path=$(pwd)

# Use HOST_IP from .env if available, otherwise detect automatically
HOST_IP="${HOST_IP:-$(hostname -I | awk '{print $1}')}"
HOST_OS_VERSION="${HOST_OS_VERSION:-$(cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '"' || echo "N/A")}"
HOST_TIMEZONE="${HOST_TIMEZONE:-$(timedatectl status | grep 'Time zone' | awk '{print $3 " (" $4 $5}' | sed 's/)//g; s/(//g' || cat /etc/timezone || echo "N/A")}"

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
    -e SUPABASE_KEY="${SUPABASE_KEY}" \
    -e SUPABASE_SERVICE_KEY="${SUPABASE_SERVICE_KEY}" \
    -e GRAFANA_PORT="${GRAFANA_PORT:-23000}" \
    --shm-size 20g \
    --restart=always \
    -w /web-manager \
    ${IMAGE_NAME}:${TAG} \
    tail -f /dev/null

