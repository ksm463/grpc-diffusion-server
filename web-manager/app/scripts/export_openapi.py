#!/usr/bin/env python3
"""
OpenAPI 스펙 추출 스크립트

이 스크립트는 FastAPI 앱에서 OpenAPI 스펙을 추출하여
/swagger/ 폴더에 JSON과 HTML 파일을 생성합니다.

사용법 (Docker 컨테이너 내부):
    docker-compose exec web-manager python app/scripts/export_openapi.py

생성 파일:
    - /swagger/openapi.json     (OpenAPI 3.0 스펙)
    - /swagger/index.html       (Swagger UI)
"""

import json
import sys
from pathlib import Path

# app 디렉토리를 Python 경로에 추가
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

# FastAPI 앱 import
try:
    from main import app
except ImportError as e:
    print(f"❌ Error: Failed to import FastAPI app from main.py")
    print(f"   Make sure you're running this from the correct directory")
    print(f"   Error details: {e}")
    sys.exit(1)


SWAGGER_UI_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
    <link rel="icon" type="image/png" href="https://fastapi.tiangolo.com/img/favicon.png">
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
        .swagger-ui .topbar {{
            display: none;
        }}
        .swagger-ui .information-container {{
            margin: 40px 0;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>

    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            window.ui = SwaggerUIBundle({{
                url: './openapi.json',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                defaultModelsExpandDepth: 1,
                defaultModelExpandDepth: 1,
                docExpansion: "list",
                filter: true,
                showRequestHeaders: true,
                tryItOutEnabled: true,
                persistAuthorization: true
            }});
        }};
    </script>
</body>
</html>
"""


def export_openapi():
    """OpenAPI 스펙을 추출하여 /swagger/ 폴더에 저장"""

    # OpenAPI 스펙 가져오기
    print("📖 Generating OpenAPI schema from FastAPI app...")
    openapi_schema = app.openapi()

    # /swagger/ 디렉토리 경로 (Docker 컨테이너 내부)
    swagger_dir = Path("/swagger")

    # 디렉토리가 없으면 생성 (볼륨 마운트로 자동 생성되지만 안전장치)
    if not swagger_dir.exists():
        print(f"⚠️  Warning: {swagger_dir} does not exist. Creating...")
        swagger_dir.mkdir(parents=True, exist_ok=True)

    # 1. OpenAPI JSON 저장
    openapi_json_path = swagger_dir / "openapi.json"
    with open(openapi_json_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)

    print(f"✅ OpenAPI JSON saved: {openapi_json_path}")

    # 2. Swagger UI HTML 저장
    info = openapi_schema.get("info", {})
    title = info.get("title", "API Documentation")

    html_content = SWAGGER_UI_HTML_TEMPLATE.format(title=title)

    index_html_path = swagger_dir / "index.html"
    with open(index_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ Swagger UI HTML saved: {index_html_path}")

    # 통계 정보 출력
    paths_count = len(openapi_schema.get("paths", {}))
    schemas_count = len(openapi_schema.get("components", {}).get("schemas", {}))
    security_schemes_count = len(
        openapi_schema.get("components", {}).get("securitySchemes", {})
    )

    print("\n" + "="*70)
    print(f"📊 API Documentation Summary")
    print("="*70)
    print(f"Title:             {title}")
    print(f"Version:           {info.get('version', 'N/A')}")
    print(f"Description:       {info.get('description', 'N/A')[:60]}...")
    print(f"API Endpoints:     {paths_count}")
    print(f"Schemas:           {schemas_count}")
    print(f"Security Schemes:  {security_schemes_count}")

    # License 정보
    license_info = info.get("license")
    if license_info:
        print(f"License:           {license_info.get('name', 'N/A')}")

    print("="*70)

    print("\n🌐 To view locally:")
    print(f"   Open file: {index_html_path}")
    print(f"   Or in host: open swagger/index.html")

    print("\n🚀 After pushing to GitHub, documentation will be available at:")
    print("   https://ksm463.github.io/grpc-diffusion-server/")

    return True


if __name__ == "__main__":
    try:
        export_openapi()
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
