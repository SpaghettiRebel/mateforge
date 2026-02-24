import uuid
from datetime import datetime
from sqlalchemy import func, ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, column_property
from auth_service.src.infrastructure.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    founder_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    about: Mapped[str | None] = mapped_column(nullable=True)
    is_private: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Staff(Base):
    __tablename__ = "staff"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('projects.id'), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, primary_key=True)
    role: Mapped[str] = mapped_column(nullable=False)


class Subscription(Base):
    __tablename__ = "subscriptions"

    subscriber_id: Mapped[uuid.UUID] = mapped_column(index=True, primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )


class Publications(Base):
    __tablename__ = "publications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('projects.id'), nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    about: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PublicationFile(Base):
    __tablename__ = "publication_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    publication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("publications.id", ondelete="CASCADE"), index=True
    )
    file_path: Mapped[str] = mapped_column(nullable=False)
    original_name: Mapped[str] = mapped_column(nullable=False)
    order: Mapped[int] = mapped_column(default=0)
