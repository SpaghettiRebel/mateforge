from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from projects_service.src.infrastructure.models import ProjectInviteType, RequestStatus, StaffRole


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    is_private: bool

class ProjectCreateSchema(ProjectBase):
    about: str | None = Field(default=None, max_length=5000)

class ProjectUpdateSchema(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    about: Optional[str] = Field(default=None, max_length=5000)
    is_private: Optional[bool] = None

class ProjectPublicSchema(ProjectBase):
    id: UUID
    avatar_path: Optional[str]
    banner_path: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class ProjectFullSchema(ProjectPublicSchema):
    founder_id: UUID
    about: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProjectStaffSchema(BaseModel):
    user_id: UUID
    role: StaffRole

    model_config = ConfigDict(from_attributes=True)

class ProjectInvitationSchema(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    sender_id: UUID
    type: ProjectInviteType
    status: RequestStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
