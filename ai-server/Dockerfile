FROM nvcr.io/nvidia/pytorch:24.05-py3 as base

# 기본 환경 설정
ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-c"]
ENV LANG=C.UTF-8
ARG POINT=unknown

# pip 및 uv 설정
RUN pip install -U --no-cache-dir pip && \
    pip install --no-cache-dir uv cupy-cuda12x

# 실행 경로 지정
WORKDIR /root
WORKDIR /ai-server

RUN rm -rf .venv && uv venv --python /usr/bin/python3.10 --system-site-packages .venv

# 생성된 가상 환경을 컨테이너의 기본 PATH에 추가
ENV PATH="/ai-server/.venv/bin:$PATH"

# 의존성 동기화 (pytest 포함됨)
COPY pyproject.toml ./
RUN uv sync --no-cache

COPY . .

# ---- Test Stage (CI용) ----
FROM base as test

# pytest는 이미 dependencies에 포함됨
# 테스트 실행 명령
CMD ["bash", "-c", "source .venv/bin/activate && pytest tests/test_basic.py -v"]

# ---- Production Stage ----
FROM base as production

ENTRYPOINT []
CMD ["tail", "-f", "/dev/null"]