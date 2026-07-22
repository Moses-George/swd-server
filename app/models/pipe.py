from datetime import datetime
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, JSON, BigInteger, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

class Pipe(BaseModel):
    __tablename__ = "pipes"
    __table_args__ = (UniqueConstraint("network_id", "ext_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    network_id: Mapped[int] = mapped_column(ForeignKey("networks.id", ondelete="CASCADE"))
    ext_id: Mapped[str] = mapped_column(String(32))
    from_ext: Mapped[str] = mapped_column(String(32))
    to_ext: Mapped[str] = mapped_column(String(32))
    diameter: Mapped[float] = mapped_column(Float)
    flow: Mapped[float] = mapped_column(Float, default=0)
    velocity: Mapped[float] = mapped_column(Float, default=0)
    headloss: Mapped[float] = mapped_column(Float, default=0)
    material: Mapped[str] = mapped_column(String(16), default="PVC")
    age: Mapped[int] = mapped_column(Integer, default=0)