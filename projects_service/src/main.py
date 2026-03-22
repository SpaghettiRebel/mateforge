import grpc
from contextlib import asynccontextmanager
from fastapi import FastAPI

from projects_service.src.presentation.routes import router as projects_router
from projects_service.src.infrastructure.generated import users_pb2_grpc


@asynccontextmanager
async def lifespan(app: FastAPI):
    channel = grpc.aio.insecure_channel("auth_service:50051")

    client = users_pb2_grpc.UsersExternalStub(channel)

    app.state.grpc_client = client
    app.state.grpc_channel = channel

    print("Connected to Auth Service via gRPC")

    yield

    print("Closing gRPC connection...")
    await channel.close()


app = FastAPI(
    title="Projects service",
    description="User's projects microservice",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(projects_router, prefix="/projects", tags=["Projects"])


@app.get("/health")
def health_check():
    return {"status": "ok"}