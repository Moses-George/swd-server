from datetime import datetime
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, JSON, BigInteger, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel

class WorkOrder(BaseModel):
    __tablename__ = "work_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    network_id: Mapped[int] = mapped_column(ForeignKey("networks.id", ondelete="CASCADE"))
    asset_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(200))
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    status: Mapped[str] = mapped_column(String(16), default="open")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())