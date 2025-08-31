# pytorch:24.05-py3를 베이스 파일로 선택
FROM nvcr.io/nvidia/pytorch:24.05-py3

# 기본 환경 설정
ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-c"]
ENV LANG=C.UTF-8
ARG POINT=unknown

# 레디스 설치
RUN apt-get update && \
    apt-get install -y redis-server && \
    rm -rf /var/lib/apt/lists/*

# pip 및 uv 설정
RUN pip install -U --no-cache-dir pip && \
    pip install --no-cache-dir uv cupy-cuda12x

# 실행 경로 지정
WORKDIR /root
WORKDIR /grpc-inference-server

RUN rm -rf .venv && uv venv --python /usr/bin/python3.10 --system-site-packages .venv

# 생성된 가상 환경을 컨테이너의 기본 PATH에 추가
ENV PATH="/grpc-inference-server/.venv/bin:$PATH"

# 의존성 동기화
COPY pyproject.toml ./
RUN uv sync --no-cache

COPY . .

ENTRYPOINT []

CMD ["/bin/bash", "-c", "redis-server /grpc-inference-server/redis.conf --daemonize yes && sleep 1 && tail -f /dev/null"]