import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from projects_service.src.infrastructure.config import settings
from projects_service.src.infrastructure.database import engine
from projects_service.src.infrastructure.grpc_client import UsersGrpcClient
from projects_service.src.infrastructure.middleware import setup_middleware
from projects_service.src.presentation.routes import router as projects_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = UsersGrpcClient(
        host=settings.AUTH_GRPC_HOST,
        port=settings.AUTH_GRPC_PORT,
        service_token=settings.GRPC_SERVICE_TOKEN,
        timeout_seconds=settings.AUTH_GRPC_TIMEOUT_SECONDS,
    )
    app.state.users_gateway = client
    logger.info("Configured Auth Service gRPC client")

    yield

    await client.close()
    await engine.dispose()


app = FastAPI(
    title="Projects service",
    description="User's projects microservice",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(projects_router, prefix="/projects", tags=["Projects"])
setup_middleware(app)


@app.get("/health")
def health_check():
    return {"status": "ok"}
