from fastapi import FastAPI

from auth_service.src.infrastructure.middleware import setup_middleware
from auth_service.src.presentation.auth_routes import router as auth_router
from auth_service.src.presentation.user_routes import router as user_router

app = FastAPI(
    title="Users service",
    description="Authentication and profile microservice",
    version="1.0.0"
)

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/users", tags=["Users"])

setup_middleware(app)

@app.get("/health")
def health_check():
    return {"status": "ok"}
