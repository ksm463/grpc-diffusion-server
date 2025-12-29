# gRPC Diffusion Server

FastAPI 웹 관리 인터페이스와 스테이블 디퓨전(Stable Diffusion) 이미지 생성을 위한 gRPC 기반 AI 추론 서버를 결합한 분산형 AI 이미지 생성 시스템입니다.

---

## 개요 (Overview)

본 시스템은 사용자가 웹 인터페이스를 통해 스테이블 디퓨전(Stable Diffusion) 모델을 사용하여 이미지를 생성할 수 있게 하며, 레디스(Redis) 큐를 통한 비동기 처리와 온프레미스(On-premis) 하드웨어 모니터링 기능을 제공합니다. 아키텍처는 AI 처리를 위한 gRPC와 웹 관리를 위한 REST API를 포함하여 잘 정의된 프로토콜을 통해 통신하는 마이크로서비스(microservices)로 구성되어 있습니다.
<div align="center">

![Image](https://github.com/user-attachments/assets/c7642e44-0d32-464a-a595-6929c16eb628)
</div>

---

## 시스템 아키텍처 (System Architecture)

이 시스템은 다음과 같은 구성 요소들을 포함하는 마이크로서비스 아키텍처(microservices architecture)로 구성됩니다.

### 애플리케이션 서비스 (Application Services)

- **ai-server**: gRPC에서 실행되는 파이토치(PyTorch) 기반 AI 추론 서버 
- **web-manager**: FastAPI 기반 웹 관리 인터페이스
- **redis-server**: 캐싱(caching) 및 메시지 큐잉(message queuing)을 위한 인메모리(in-memory) 데이터 저장소

### 모니터링 서비스 (Monitoring Services)

- **prometheus**: 메트릭(metrics) 수집 및 시계열(time-series) 데이터베이스 
- **grafana**: 메트릭 시각화 대시보드
- **node-exporter**: 호스트 시스템 리소스(CPU, MEM 등) 메트릭 수집
- **nvidia-dcgm-exporter**: 엔비디아(NVIDIA) GPU 상세 메트릭 수집

---

## 주요 기능 (Key Features)

- **비동기 처리 (Asynchronous Processing):** 확장 가능한 이미지 생성을 위한 레디스(Redis) 기반 작업 큐잉
- **gRPC 통신 (gRPC Communication):** 고성능 서비스 간 통신 
- **사용자 인증 (User Authentication):** JWT 토큰을 사용한 Supabase 연동 
- **GPU 지원 (GPU Support):** GPU 가속을 위한 엔비디아 컨테이너 툴킷(NVIDIA Container Toolkit) 연동 
- **포괄적인 모니터링 (Comprehensive Monitoring):** 그라파나(Grafana) 대시보드를 사용한 프로메테우스(Prometheus) 메트릭
- **웹 인터페이스 (Web Interface):** 사용자 친화적인 스테이블 디퓨전(Stable Diffusion) 스튜디오

---

## 설치 요구사항 (Prerequisites)

서버를 실행하기 전에 호스트 머신에 다음 소프트웨어가 설치되어 있어야 합니다.

- 도커 (Docker)
- 도커 컴포즈 (Docker Compose)
- 엔비디아 드라이버 (NVIDIA Driver)
- 엔비디아 컨테이너 툴킷 (NVIDIA Container Toolkit)
---

## 실행 방법 (Run system)

### 1. 환경 구성 (Environment Configuration)

프로젝트 루트 디렉터리에 `.env` 파일을 생성하고 환경에 맞게 변수를 설정해야 합니다.
먼저, 아래 명령어로 예제 파일을 복사합니다.
```bash
cp .env.example .env
```

그 다음, .env 파일을 열어 반드시 다음 변수들을 사용자의 환경에 맞게 수정하세요.

- HOST_IP: 사용자의 서버 IP 주소
- SUPABASE_KEY 및 SUPABASE_SERVICE_KEY: 사용자의 Supabase 인증 정보 

### 2. 빌드 및 실행 (Build and Run)

모든 서비스를 백그라운드에서 빌드하고 시작합니다.

```bash
docker compose up -d --build
```

이후 코드 변경 없이 실행할 경우:
```bash
docker compose up -d
```


### 3. 서비스 접근 (Service Access)

실행 후, 다음 URL에서 서비스에 접근할 수 있습니다.

| 서비스 | 포트 | URL | 설명 |
| :--- | :--- | :--- | :--- |
| 웹 관리자 (Web Manager) | 27000, 28000 | `http://<HOST_IP>:27000` | 웹 관리 UI |
| 프로메테우스 (Prometheus) | 29090 | `http://<HOST_IP>:29090` | 메트릭 쿼리 및 대상 상태 |
| 그라파나 (Grafana) | 23000 | `http://<HOST_IP>:23000` | 모니터링 대시보드 |
| 레디스 (Redis) | 6379 | `redis-cli -h <HOST_IP> -p 6379` | CLI 접근 |
| AI 서버 (AI Server) | 20051 | - | gRPC 통신 포트 |

---

## 📖 API 문서 (API Documentation)

**온라인 API 문서:**

https://ksm463.github.io/grpc-diffusion-server/

대화형 API 문서는 FastAPI를 기반으로 하는 0Swagger UI로 확인 가능합니다. 모든 Web Manager의 엔드포인트, 요청/응답 스키마, 인증 방법을 확인할 수 있습니다.

**로컬에서 문서 생성:**

```bash
# web-manager 컨테이너에서 실행
docker-compose exec web-manager python app/scripts/export_openapi.py

# 생성된 문서 확인
open swagger/index.html
```

자세한 내용은 [swagger/README.md](swagger/README.md)를 참조하세요.

---

## 사용법 (Usage)

### 이미지 생성 (Image Generation)

시스템은 다음 흐름을 통해 이미지 생성 요청을 처리합니다.

1. 사용자가 웹 인터페이스를 통해 요청을 제출합니다.

2. 웹 관리자가 사용자 인증을 검증하고 gRPC를 통해 AI 서버로 요청을 전달합니다.

3. AI 서버가 레디스(Redis)에 작업을 큐잉하고 스테이블 디퓨전(Stable Diffusion)으로 처리합니다.

4. 생성된 이미지는 Supabase에 저장되고 URL이 페이지에 반환됩니다. 

<div align="center">

<img width="1072" height="1077" alt="Image" src="https://github.com/user-attachments/assets/d0d83a48-a381-4841-bb70-6877b93cd49a" />
<img width="1681" height="1072" alt="Image" src="https://github.com/user-attachments/assets/0916a961-9ac3-45d1-8a61-6153cd0a7aca" />
<img width="1359" height="1076" alt="Image" src="https://github.com/user-attachments/assets/cff72e2b-e937-4ba9-99bf-df1e029ed776" />
</div>

---

## 모니터링 설정 (Monitoring Setup)

GPU 모니터링을 위해, 공식 엔비디아(NVIDIA) DCGM 대시보드를 가져오세요.

1. `http://<HOST_IP>:23000` 주소로 그라파나(Grafana)에 접속합니다.
2. `Dashboards` → `New` → `Import`로 이동합니다.
3. 대시보드 ID `12239`를 입력하고 데이터 소스로 프로메테우스(Prometheus)를 선택합니다. 

---

## 기술 스택 (Technology Stack)

- **백엔드 (Backend):** uvicorn 서버를 사용하는 FastAPI
- **AI 처리 (AI Processing):** 스테이블 디퓨전(Stable Diffusion) 모델을 사용하는 파이토치(PyTorch)
- **서비스 간 통신 (Inter-Service Communication):** gRPC 프로토콜
- **메시지 큐 (Message Queue):** 비동기 작업 처리를 위한 레디스(Redis)
- **인증 및 저장소 (Authentication & Storage):** Supabase 연동
- **모니터링 (Monitoring):** 프로메테우스(Prometheus) + 그라파나(Grafana)
- **컨테이너화 (Containerization):** GPU를 지원하는 도커(Docker)
- **패키지 관리 (Package Management):** 파이썬(Python) 의존성 관리를 위한 UV

---

## 구성 (Configuration)

주요 구성 환경은 환경 변수와 도커 컴포즈(Docker Compose) 설정을 통해 관리되도록 하였습니다. 시스템 자원을 확인할 수 있는 모니터링 기능을 제공합니다.

상세한 구성 옵션은 `.env.example` 파일과 `docker-compose.yml` 내용을 참조하세요.

---
