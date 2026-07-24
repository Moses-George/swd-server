from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from sqlalchemy import  DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
import uuid


class BaseModel(Base):
    __abstract__ = True

    # id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())