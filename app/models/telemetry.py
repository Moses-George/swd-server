from datetime import datetime
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, JSON, BigInteger, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel

class Telemetry(BaseModel):
    __tablename__ = "telemetry"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    network_id: Mapped[int] = mapped_column(ForeignKey("networks.id", ondelete="CASCADE"))
    node_ext: Mapped[str] = mapped_column(String(32))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    metric: Mapped[str] = mapped_column(String(32))
    value: Mapped[float] = mapped_column(Float)