from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Trigger reload
from app.api.api import api_router
from app.core.config import settings

app = FastAPI(title="SciAgent Backend", version="1.0.0")

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(origin).strip("/") for origin in settings.BACKEND_CORS_ORIGINS
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"message": "Welcome to SciAgent API"}
