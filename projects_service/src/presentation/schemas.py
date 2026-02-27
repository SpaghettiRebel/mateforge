from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class ProjectBase(BaseModel):
    name: str
    is_private: bool

class ProjectCreateSchema(ProjectBase):
    about: str

class ProjectPublicSchema(ProjectBase):
    id: UUID
    avatar_path: Optional[str]
    banner_path: Optional[str]

    class Config:
        from_attributes = True

class ProjectFullSchema(ProjectPublicSchema):
    founder_id: UUID
    about: str
    created_at: datetime

    class Config:
        from_attributes = True