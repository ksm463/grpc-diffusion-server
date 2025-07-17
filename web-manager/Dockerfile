FROM python:3.12-slim

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Seoul

RUN apt-get update && apt-get install -y tzdata && \
    ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime && \
    apt-get install -y libturbojpeg0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /web-manager

COPY setting-scripts/ ./setting-scripts/
RUN bash ./setting-scripts/install_dependencies.sh

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache

COPY . .