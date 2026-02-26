from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth_service.src.infrastructure.config import settings

def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], #allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
