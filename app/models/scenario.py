from datetime import datetime
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, JSON, BigInteger, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

class Scenario(BaseModel):
    __tablename__ = "scenarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    network_id: Mapped[int] = mapped_column(ForeignKey("networks.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(32))
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    baseline_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scenario_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())