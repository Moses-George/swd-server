from datetime import datetime
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, JSON, BigInteger, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

class Node(BaseModel):
    __tablename__ = "nodes"
    __table_args__ = (UniqueConstraint("network_id", "ext_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    network_id: Mapped[int] = mapped_column(ForeignKey("networks.id", ondelete="CASCADE"))
    ext_id: Mapped[str] = mapped_column(String(32))
    type: Mapped[str] = mapped_column(String(16))
    label: Mapped[str] = mapped_column(String(120))
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    pressure: Mapped[float] = mapped_column(Float, default=0)
    demand: Mapped[float | None] = mapped_column(Float, nullable=True)
    level: Mapped[float | None] = mapped_column(Float, nullable=True)
    rated_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation: Mapped[float | None] = mapped_column(Float, nullable=True)
    leak_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="ok")