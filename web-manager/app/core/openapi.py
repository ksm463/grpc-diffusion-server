from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def create_custom_openapi(app: FastAPI):
    """
    Custom OpenAPI schema generator with enhanced JWT security documentation

    Args:
        app: FastAPI application instance

    Returns:
        Callable that generates and caches the OpenAPI schema
    """
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            contact=app.contact,
            license_info=app.license_info,
        )

        # Add JWT Bearer authentication scheme
        openapi_schema["components"]["securitySchemes"] = {
            "HTTPBearer": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Enter your Supabase JWT token"
            }
        }

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    return custom_openapi
