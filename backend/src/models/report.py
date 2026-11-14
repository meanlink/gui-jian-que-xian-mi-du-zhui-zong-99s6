from sqlalchemy import String, Double, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class Report(Base):
    __tablename__ = 'reports'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    job_id: Mapped[int] = mapped_column(ForeignKey('jobs.id'))
    destination: Mapped[str] = mapped_column(String(120))
    interval_seconds: Mapped[int]
    next_run: Mapped[float] = mapped_column(Double)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # 计划创建时所依据的授权；授权撤回后计划随之一同封存，且不可再启用
    authorization_id: Mapped[int | None] = mapped_column(ForeignKey('authorizations.id'), nullable=True)
    sealed: Mapped[bool] = mapped_column(Boolean, default=False)
    sealed_at: Mapped[float | None] = mapped_column(Double, nullable=True)
    sealed_reason: Mapped[str] = mapped_column(String(1000), default='')
class Delivery(Base):
    __tablename__ = 'deliveries'
    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey('reports.id'))
    created_at: Mapped[float] = mapped_column(Double)
    checksum: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(160))
    destination: Mapped[str] = mapped_column(String(120))
    # 封存后简报记录保留用于查证，但拒绝一切下载
    sealed: Mapped[bool] = mapped_column(Boolean, default=False)
    sealed_at: Mapped[float | None] = mapped_column(Double, nullable=True)
