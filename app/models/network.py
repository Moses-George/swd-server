from datetime import datetime
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, JSON, BigInteger, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
from .node import Node
from .pipe import Pipe


class Network(BaseModel):
    __tablename__ = "networks"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    nodes: Mapped[list["Node"]] = relationship(cascade="all, delete-orphan")
    pipes: Mapped[list["Pipe"]] = relationship(cascade="all, delete-orphan")
