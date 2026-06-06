import asyncio
import logging

import grpc

from auth_service.src.infrastructure.generated import users_pb2_grpc
from auth_service.src.presentation.grpc_handler import UsersServicer

logger = logging.getLogger(__name__)


async def serve_grpc(port: int):
    server = grpc.aio.server(
        options=[
            ("grpc.max_receive_message_length", 64 * 1024),
            ("grpc.max_send_message_length", 64 * 1024),
        ]
    )

    users_pb2_grpc.add_UsersExternalServicer_to_server(
        UsersServicer(), server
    )

    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)

    logger.info("gRPC server started on %s", listen_addr)

    await server.start()

    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        await server.stop(5)
