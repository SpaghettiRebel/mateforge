import hmac
import logging
from uuid import UUID

import grpc
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from auth_service.src.infrastructure.config import settings
from auth_service.src.infrastructure.database import async_session_factory
from auth_service.src.infrastructure.generated import users_pb2, users_pb2_grpc
from auth_service.src.infrastructure.models import UserDB

logger = logging.getLogger(__name__)


class UsersServicer(users_pb2_grpc.UsersExternalServicer):
    async def GetUserExistence(
            self,
            request: users_pb2.UserRequest,
            context: grpc.aio.ServicerContext
    ) -> users_pb2.ExistenceResponse:
        metadata = dict(context.invocation_metadata())
        provided_token = metadata.get("x-service-token", "")
        if not hmac.compare_digest(provided_token, settings.GRPC_SERVICE_TOKEN):
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Service authentication failed")

        try:
            user_id = UUID(request.user_id)
        except ValueError:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid user id")

        async with async_session_factory() as session:
            try:
                query = select(UserDB).where(UserDB.id == user_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()

                if user:
                    return users_pb2.ExistenceResponse(exists=True)

                return users_pb2.ExistenceResponse(exists=False)

            except SQLAlchemyError:
                logger.exception("Database failure while checking user existence")
                await context.abort(grpc.StatusCode.INTERNAL, "Internal service error")
