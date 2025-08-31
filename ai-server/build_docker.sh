#!/bin/bash

IMAGE_NAME="grpc-server-image"
TAG="0.1"

docker build --no-cache --build-arg POINT=1.0 -t ${IMAGE_NAME}:${TAG} -f Dockerfile .
