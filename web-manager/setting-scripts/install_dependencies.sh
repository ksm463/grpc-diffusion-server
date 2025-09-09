#!/bin/bash
apt-get update

apt-get update && apt-get install -y \
    git unzip vim tmux wget

apt-get install -y \
    libgl1 libglib2.0-0\