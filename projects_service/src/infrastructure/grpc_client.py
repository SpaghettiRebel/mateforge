import logging
from uuid import UUID

import grpc

from projects_service.src.infrastructure.exceptions import ExternalServiceUnavailable

from .generated import users_pb2, users_pb2_grpc

logger = logging.getLogger(__name__)


class UsersGrpcClient:
    def __init__(self, host: str, port: int, service_token: str, timeout_seconds: float):
        self.addr = f"{host}:{port}"
        self.service_token = service_token
        self.timeout_seconds = timeout_seconds
        self._channel: grpc.aio.Channel | None = None
        self._stub: users_pb2_grpc.UsersExternalStub | None = None

    def _get_channel(self) -> grpc.aio.Channel:
        if self._channel is None:
            self._channel = grpc.aio.insecure_channel(
                self.addr,
                options=[
                    ("grpc.max_receive_message_length", 64 * 1024),
                    ("grpc.max_send_message_length", 64 * 1024),
                ],
            )
        return self._channel

    def _get_stub(self) -> users_pb2_grpc.UsersExternalStub:
        if self._stub is None:
            channel = self._get_channel()
            self._stub = users_pb2_grpc.UsersExternalStub(channel)
        return self._stub

    async def check_user_exists(self, user_id: UUID) -> bool:
        stub = self._get_stub()
        try:
            response = await stub.GetUserExistence(
                users_pb2.UserRequest(user_id=str(user_id)),
                timeout=self.timeout_seconds,
                metadata=(("x-service-token", self.service_token),),
            )
            return response.exists
        except grpc.aio.AioRpcError as exc:
            logger.warning("Auth gRPC call failed with status %s", exc.code())
            raise ExternalServiceUnavailable("Auth service is unavailable") from exc

    async def close(self):
        if self._channel:
            await self._channel.close()
