# Docker Compose를 이용한 서버 실행 가이드

이 문서는 `docker-compose.yml` 파일을 사용하여 AI 서버, 웹 관리자 및 모니터링 시스템을 한 번에 실행하는 방법을 안내합니다.

## 1. 시스템 구성 요소

본 Docker Compose 환경은 다음과 같은 서비스(services)로 구성됩니다.

* **애플리케이션(Application)**
  * `ai-server`: PyTorch 기반의 AI 추론 서버(Inference Server)
  * `web-manager`: FastAPI 기반의 웹 관리자(Web Manager)
  * `redis-server`: 데이터 캐싱 및 메시지 큐를 위한 인메모리(in-memory) 데이터 저장소

* **모니터링(Monitoring)**
  * `prometheus`: 메트릭(metric) 수집 및 시계열 데이터베이스(TSDB)
  * `grafana`: 메트릭(metric) 시각화를 위한 대시보드(dashboard)
  * `node-exporter`: 호스트(host)의 CPU, 메모리 등 시스템 자원 메트릭(metric) 수집
  * `nvidia-dcgm-exporter`: NVIDIA GPU의 상세 메트릭(metric) 수집 (NVIDIA 공식 Exporter)

---

## 2. 사전 준비 사항

서버를 실행하기 전에 호스트(host) 머신에 다음 소프트웨어들이 설치되어 있어야 합니다.

* [Docker](https://docs.docker.com/engine/install/)
* [Docker Compose](https://docs.docker.com/compose/install/)
* [NVIDIA 드라이버](https://www.nvidia.com/Download/index.aspx)
* [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

---

## 3. 초기 설정

프로젝트 루트(root) 디렉터리에 `docker-compose.yml`과 `prometheus.yml` 외에, 실행 환경을 정의하는 `.env` 파일이 필요합니다.

### `.env` 파일 생성

아래 내용을 복사하여 프로젝트 루트(root)에 `.env` 파일을 생성하세요. **`HOST_IP`를 포함한 호스트 환경 변수는 반드시 자신의 환경에 맞게 수정해야 합니다.**

```dotenv
# .env

# ==============================
#      공통 설정 (Common Settings)
# ==============================
PORT_NUM=2
SHARED_SHM_SIZE=20g

# ==============================
#   AI 서버 설정 (AI Server Settings)
# ==============================
AI_SERVER_IMAGE_NAME=grpc-server-image
AI_SERVER_IMAGE_TAG=0.1
AI_SERVER_BUILD_ARG_POINT=1.0

# =================================
#  웹 관리자 설정 (Web Manager Settings)
# =================================
WEB_MANAGER_IMAGE_NAME=web-manager
WEB_MANAGER_IMAGE_TAG=0.1

# ==================================
#  호스트 환경 변수 (Host Environment Variables)
# ==================================
# 아래 값들은 터미널 명령어를 통해 확인 후 사용자의 환경에 맞게 수정해주세요.
HOST_IP=192.168.0.10 # hostname -I | awk '{print $1}'
HOST_OS_VERSION="Ubuntu 22.04.4 LTS" # cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '"'
HOST_TIMEZONE=Asia/Seoul # timedatectl status | grep 'Time zone' | awk '{print $3}'
DISPLAY=:0

# ==================================
#  데이터베이스 설정 (Database Settings)
# ==================================
SUPABASE_KEY="YOUR_SUPABASE_KEY"
SUPABASE_SERVICE_KEY="YOUR_SUPABASE_SERVICE_KEY"

# ==============================
#   레디스 설정 (Redis Settings)
# ==============================
REDIS_IMAGE_NAME=redis
REDIS_IMAGE_TAG=6.0.16
REDIS_PORT=6379

# ==================================
#  모니터링 설정 (Monitoring Settings)
# ==================================
# Prometheus
PROMETHEUS_PORT=29090
PROMETHEUS_IMAGE_TAG=v3.3.0

# Grafana
GRAFANA_PORT=23000
GRAFANA_IMAGE_TAG=11.6.1

# Node Exporter (CPU, RAM)
NODE_EXPORTER_PORT=29440
NODE_EXPORTER_IMAGE_TAG=v1.9.0


# DCGM Exporter (GPU) - NVIDIA 공식
DCGM_EXPORTER_PORT=29400
DCGM_EXPORTER_IMAGE_TAG=3.3.5-3.1.8-ubuntu22.04

```

## 4. 주요 명령어

모든 명령어는 `docker-compose.yml` 파일이 있는 프로젝트 루트(root) 디렉터리에서 실행합니다.

### 빌드 및 실행

-   모든 서비스를 **빌드(build)하고 백그라운드에서 실행**합니다.
    ```bash
    docker compose up -d --build
    ```
-   코드 변경 없이 **다시 시작**할 때는 `--build` 옵션을 생략할 수 있습니다.
    ```bash
    docker compose up -d
    ```

### 상태 확인

-   현재 실행 중인 컨테이너(container)들의 상태를 확인합니다.
    ```bash
    docker compose ps
    ```

### 로그 확인

-   특정 서비스(service)의 실시간 로그(log)를 확인합니다. 디버깅에 유용합니다.
    ```bash
    # AI 서버 로그 확인
    docker compose logs -f ai-server

    # 웹 관리자 로그 확인
    docker compose logs -f web-manager

    # GPU Exporter 로그 확인
    docker compose logs -f nvidia-dcgm-exporter
    ```

### 종료 및 삭제

-   실행 중인 모든 **컨테이너(container)와 네트워크(network)를 중지하고 삭제**합니다.
    ```bash
    docker compose down
    ```
-   컨테이너(container), 네트워크(network)와 함께 직접 **빌드(build)한 이미지(image)까지 삭제**합니다.
    ```bash
    docker compose down --rmi local
    ```

---

## 5. 서비스 접속 정보

서비스가 정상적으로 실행되면 아래 주소로 각 UI에 접속할 수 있습니다.

| 서비스 (Service) | 포트 (Port) | 접속 주소 (URL) | 설명 |
| :--- | :--- | :--- | :--- |
| **Web Manager** | 27000, 28000 | `http://<HOST_IP>:27000` | 웹 관리자 UI |
| **Prometheus** | 29090 | `http://<HOST_IP>:29090` | 메트릭(metric) 쿼리(query) 및 타겟(target) 상태 확인 |
| **Grafana** | 23000 | `http://<HOST_IP>:23000` | 모니터링 대시보드(dashboard) |
| **Redis** | 6379 | `redis-cli -h <HOST_IP> -p 6379` | CLI를 통한 접속 |
| **AI Server** | 20051 등 | - | gRPC 통신 포트 |

---

## 6. 그라파나 대시보드 설정

GPU 모니터링을 위해 NVIDIA의 공식 DCGM 대시보드(dashboard)를 사용하는 것을 권장합니다.

1.  그라파나(`http://<HOST_IP>:23000`)에 접속합니다.
2.  왼쪽 메뉴에서 **Dashboards**로 이동합니다.
3.  오른쪽 상단의 **New** 버튼을 누르고 **Import**를 선택합니다.
4.  `Import via grafana.com` 입력란에 ID **`12239`** 를 입력하고 **Load** 버튼을 누릅니다.
5.  다음 화면에서 데이터 소스(data source)를 **Prometheus**로 선택하고 **Import** 버튼을 누르면 설치가 완료됩니다.

이제 **NVIDIA DCGM Exporter Dashboard**를 통해 실시간으로 GPU 상태를 모니터링할 수 있습니다.

