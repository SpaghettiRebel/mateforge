from fastapi import FastAPI
from projects_service.src.presentation.routes import router as router

app = FastAPI(
    title="Projects service",
    description="User's projects microservice",
    version="1.0.0"
)

app.include_router(router, prefix="/projects", tags=["Projects"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
