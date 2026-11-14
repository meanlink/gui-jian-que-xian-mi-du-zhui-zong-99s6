from sqlalchemy import String, Double, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base

class Authorization(Base):
    """一次批准即形成一份使用授权；撤回仅让当前授权失效，历史授权始终保留。"""
    __tablename__ = 'authorizations'
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('jobs.id'))
    sequence: Mapped[int]
    status: Mapped[str] = mapped_column(String(20), default='active')
    reason: Mapped[str] = mapped_column(Text, default='')
    granted_by: Mapped[str] = mapped_column(String(150))
    granted_at: Mapped[float] = mapped_column(Double)
    revoked_by: Mapped[str | None] = mapped_column(String(150), nullable=True)
    revoked_at: Mapped[float | None] = mapped_column(Double, nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
