from typing import Optional
from uuid import UUID

import grpc

from .generated import users_pb2, users_pb2_grpc


class UsersGrpcClient:
    def __init__(self, host: str, port: int):
        self.addr = f"{host}:{port}"
        self._channel: Optional[grpc.aio.Channel] = None
        self._stub: Optional[users_pb2_grpc.UsersExternalStub] = None

    async def _get_channel(self) -> grpc.aio.Channel:
        if self._channel is None:
            # Настройка канала (можно добавить keep-alive, таймауты и т.д.)
            self._channel = grpc.aio.insecure_channel(self.addr)
        return self._channel

    async def _get_stub(self) -> users_pb2_grpc.UsersExternalStub:
        if self._stub is None:
            channel = await self._get_channel()
            self._stub = users_pb2_grpc.UsersExternalStub(channel)
        return self._stub

    async def check_user_exists(self, user_id: UUID) -> bool:
        stub = await self._get_stub()
        try:
            response = await stub.GetUserExistence(
                users_pb2.UserRequest(user_id=str(user_id)),
                timeout=2.0
            )
            return response.exists
        except grpc.aio.AioRpcError as e:
            print(f"gRPC Error: {e.code()} - {e.details()}")
            return False

    async def close(self):
        if self._channel:
            await self._channel.close()