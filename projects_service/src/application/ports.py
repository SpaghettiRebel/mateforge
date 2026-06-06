from typing import Protocol
from uuid import UUID


class UsersGateway(Protocol):
    async def check_user_exists(self, user_id: UUID) -> bool:
        ...
