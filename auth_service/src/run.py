import asyncio
import uvicorn

from auth_service.src.main import app
from auth_service.src.infrastructure.config import settings
from auth_service.src.grpc_main import serve_grpc


async def main():
    grpc_task = asyncio.create_task(
        serve_grpc(settings.GRPC_PORT)
    )

    config = uvicorn.Config(
        app,
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=False,
        log_level=settings.LOG_LEVEL,
    )

    server = uvicorn.Server(config)

    await asyncio.gather(
        grpc_task,
        server.serve(),
    )


if __name__ == "__main__":
    asyncio.run(main())