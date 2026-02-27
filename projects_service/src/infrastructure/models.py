import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import func, ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, column_property
from projects_service.src.infrastructure.database import Base


class RequestStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class ProjectInviteType(str, Enum):
    INVITE = "invite"
    REQUEST = "request"

class StaffRole(str, Enum):
    FOUNDER = "founder"
    ADMIN = "admin"
    MANAGER = "manager"
    PARTICIPANT = "participant"

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    founder_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    about: Mapped[str | None] = mapped_column(nullable=True)
    is_private: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    avatar_path: Mapped[str | None] = mapped_column(nullable=True)
    banner_path: Mapped[str | None] = mapped_column(nullable=True)

    staff: Mapped[list["Staff"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    publications: Mapped[list["Publication"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    invitations: Mapped[list["ProjectInvitation"]] = relationship(back_populates="project",
                                                                  cascade="all, delete-orphan")


class Staff(Base):
    __tablename__ = "staff"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('projects.id', ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, primary_key=True)
    role: Mapped[str] = mapped_column(nullable=False)

    project: Mapped["Project"] = relationship(back_populates="staff")


class ProjectInvitation(Base):
    __tablename__ = "project_invitations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('projects.id', ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    sender_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    type: Mapped[ProjectInviteType] = mapped_column(nullable=False)
    status: Mapped[RequestStatus] = mapped_column(default=RequestStatus.PENDING, index=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="invitations")

class Subscription(Base):
    __tablename__ = "subscriptions"

    subscriber_id: Mapped[uuid.UUID] = mapped_column(index=True, primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )

    project: Mapped["Project"] = relationship(back_populates="subscriptions")


class Publication(Base):
    __tablename__ = "publications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('projects.id', ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    about: Mapped[str | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    project: Mapped["Project"] = relationship(back_populates="publications")
    files: Mapped[list["PublicationFile"]] = relationship(back_populates="publication", cascade="all, delete-orphan")

class PublicationFile(Base):
    __tablename__ = "publication_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    publication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("publications.id", ondelete="CASCADE"), index=True
    )
    file_path: Mapped[str] = mapped_column(nullable=False)
    file_type: Mapped[str] = mapped_column(nullable=False)
    original_name: Mapped[str] = mapped_column(nullable=False)
    order: Mapped[int] = mapped_column(default=0)

    publication: Mapped["Publication"] = relationship(back_populates="files")
