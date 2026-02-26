from sqlalchemy.ext.asyncio import AsyncSession

class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
