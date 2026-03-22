import asyncio
import grpc
from auth_service.src.infrastructure.generated import users_pb2_grpc
from auth_service.src.presentation.grpc_handler import UsersServicer


async def serve_grpc(port: int):
    server = grpc.aio.server()

    users_pb2_grpc.add_UsersExternalServicer_to_server(
        UsersServicer(), server
    )

    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)

    print(f"[gRPC] started on {listen_addr}")

    await server.start()

    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        await server.stop(5)