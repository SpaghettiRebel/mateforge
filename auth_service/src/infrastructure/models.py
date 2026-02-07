import uuid
from datetime import datetime
from sqlalchemy import func, ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, column_property
from auth_service.src.infrastructure.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    subscriber_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )


class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    is_verified: Mapped[bool] = mapped_column(default=False)
    bio: Mapped[str | None] = mapped_column(nullable=True)

    following: Mapped[list["UserDB"]] = relationship(
        "UserDB",
        secondary="subscriptions",
        primaryjoin="UserDB.id == Subscription.subscriber_id",
        secondaryjoin="UserDB.id == Subscription.author_id",
        back_populates="followers"
    )

    followers: Mapped[list["UserDB"]] = relationship(
        "UserDB",
        secondary="subscriptions",
        primaryjoin="UserDB.id == Subscription.author_id",
        secondaryjoin="UserDB.id == Subscription.subscriber_id",
        back_populates="following"
    )

    followers_count: Mapped[int] = column_property(
        select(func.count(Subscription.subscriber_id))
        .where(Subscription.author_id == id)
        .correlate_except(Subscription)
        .scalar_subquery()
    )

    following_count: Mapped[int] = column_property(
        select(func.count(Subscription.author_id))
        .where(Subscription.subscriber_id == id)
        .correlate_except(Subscription)
        .scalar_subquery()
    )
