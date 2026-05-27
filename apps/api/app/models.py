from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    projects = relationship("Project", back_populates="client", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="admin")
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    amount_usd: Mapped[float] = mapped_column(Float)
    recurrence: Mapped[str] = mapped_column(String(50), default="monthly")
    rate_type: Mapped[str] = mapped_column(String(50), default="tts_selling")
    next_invoice_date: Mapped[date] = mapped_column(Date)
    billing_currency: Mapped[str] = mapped_column(String(3), default="USD")
    amount_ghs: Mapped[float | None] = mapped_column(Float, nullable=True)
    rate_source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    client = relationship("Client", back_populates="projects")


class FxRate(Base):
    __tablename__ = "fx_rates"
    __table_args__ = (UniqueConstraint("rate_date", "code", name="uq_fx_rates_date_code"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rate_date: Mapped[date] = mapped_column(Date)
    code: Mapped[str] = mapped_column(String(10), default="USD")
    cash_buying: Mapped[float] = mapped_column(Float)
    cash_selling: Mapped[float] = mapped_column(Float)
    tts_buying: Mapped[float] = mapped_column(Float)
    tts_selling: Mapped[float] = mapped_column(Float)
    source_url: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("project_id", "invoice_date", name="uq_project_invoice_date"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    invoice_date: Mapped[date] = mapped_column(Date)
    amount_usd: Mapped[float] = mapped_column(Float)
    fx_rate: Mapped[float] = mapped_column(Float)
    amount_ghs: Mapped[float] = mapped_column(Float)
    rate_type: Mapped[str] = mapped_column(String(50))
    source_rate_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    rate_pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)


class JobLog(Base):
    __tablename__ = "job_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SchedulerLock(Base):
    __tablename__ = "scheduler_locks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    owner_id: Mapped[str] = mapped_column(String(100))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
