from pydantic import BaseModel, Field


class HostSystemInfo(BaseModel):
    """
    호스트 시스템 정보 응답
    """
    host_ip_address: str = Field(..., description="호스트 서버 IP 주소")
    host_os_version: str = Field(..., description="호스트 OS 버전")
    host_timezone: str = Field(..., description="호스트 타임존")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "host_ip_address": "192.168.100.50",
                    "host_os_version": "Ubuntu 22.04.3 LTS",
                    "host_timezone": "Asia/Seoul"
                }
            ]
        }


class ClientIPResponse(BaseModel):
    """
    클라이언트 IP 주소 응답
    """
    client_ip: str = Field(..., description="클라이언트 IP 주소")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "client_ip": "192.168.100.10"
                }
            ]
        }


class GrpcInfoResponse(BaseModel):
    """
    gRPC 서버 정보 응답
    """
    grpc_port: str = Field(..., description="gRPC 서버 포트")
    server_status: str = Field(..., description="서버 상태")
    message: str = Field(..., description="추가 메시지")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "grpc_port": "20051",
                    "server_status": "Running",
                    "message": "gRPC server is operational"
                }
            ]
        }
