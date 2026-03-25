import grpc
from sqlalchemy import select

from auth_service.src.infrastructure.database import async_session_factory
from auth_service.src.infrastructure.generated import users_pb2, users_pb2_grpc
from auth_service.src.infrastructure.models import UserDB


class UsersServicer(users_pb2_grpc.UsersExternalServicer):
    async def GetUserExistence(
            self,
            request: users_pb2.UserRequest,
            context: grpc.aio.ServicerContext
    ) -> users_pb2.ExistenceResponse:

        user_id = request.user_id

        async with async_session_factory() as session:
            try:
                query = select(UserDB).where(UserDB.id == user_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()

                if user:
                    return users_pb2.ExistenceResponse(exists=True)

                return users_pb2.ExistenceResponse(exists=False)

            except Exception as e:
                print(f"gRPC Error: {e}")
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(f"Database error: {str(e)}")
                return users_pb2.ExistenceResponse(exists=False)
