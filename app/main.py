from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Trigger reload
from fastapi.responses import JSONResponse
from app.api.api import api_router
from app.infrastructure.events.handlers import register_event_handlers

# --- Setup LangSmith & other observability ---
from app.core import observability
from app.core.config import settings

# Iniciar rastreamento assim que a app sobe, se habilitado
try:
    if hasattr(observability, "setup_tracing"):
        observability.setup_tracing()
except AttributeError:
    pass


# Registrar observadores de Eventos do Dominio
register_event_handlers()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup observability
    observability.setup_langfuse()
    yield
    # Clean up observability if needed
    observability.teardown_langfuse()


app = FastAPI(title="SciAgent Backend", version="1.0.0", lifespan=lifespan)

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
