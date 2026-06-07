from contextlib import asynccontextmanager

from fastapi import FastAPI

from auth_service.src.infrastructure.database import engine
from auth_service.src.infrastructure.middleware import setup_middleware
from auth_service.src.infrastructure.redis import close_redis_pool
from auth_service.src.presentation.auth_routes import router as auth_router
from auth_service.src.presentation.skill_routes import router as skill_router
from auth_service.src.presentation.user_routes import router as user_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await close_redis_pool()
    await engine.dispose()


app = FastAPI(
    title="Users service",
    description="Authentication and profile microservice",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/users", tags=["Users"])
app.include_router(skill_router, prefix="/skills", tags=["Skills"])

setup_middleware(app)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
