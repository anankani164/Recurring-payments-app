import os
import smtplib
from datetime import date
from email.message import EmailMessage

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import FxRate, Invoice, JobLog, Project
from .observability import log_event


def get_rate_value(rate: FxRate, rate_type: str) -> float:
    mapping = {
        "cash_buying": rate.cash_buying,
        "cash_selling": rate.cash_selling,
        "tts_buying": rate.tts_buying,
        "tts_selling": rate.tts_selling,
    }
    if rate_type not in mapping:
        raise ValueError(f"Unsupported rate type: {rate_type}")
    return mapping[rate_type]


def next_date_for_recurrence(current_date: date, recurrence: str) -> date:
    if recurrence == "weekly":
        return current_date + relativedelta(weeks=1)
    if recurrence == "monthly":
        return current_date + relativedelta(months=1)
    raise ValueError(f"Unsupported recurrence: {recurrence}")


def resolve_rate_for_date(db: Session, invoice_date: date) -> FxRate:
    rate = db.execute(
        select(FxRate).where(FxRate.rate_date <= invoice_date).order_by(FxRate.rate_date.desc())
    ).scalars().first()
    if rate:
        return rate

    latest_rate = db.execute(select(FxRate).order_by(FxRate.rate_date.desc())).scalars().first()
    if latest_rate:
        return latest_rate

    raise ValueError("No FX rate available")


def generate_invoice_for_project(db: Session, project: Project, invoice_date: date) -> Invoice:
    existing = db.execute(
        select(Invoice).where(Invoice.project_id == project.id, Invoice.invoice_date == invoice_date)
    ).scalars().first()
    if existing:
        return existing

    rate = resolve_rate_for_date(db, invoice_date)
    fx = get_rate_value(rate, project.rate_type)
    amount_ghs = round(project.amount_usd * fx, 2)
    invoice = Invoice(
        project_id=project.id,
        invoice_date=invoice_date,
        amount_usd=project.amount_usd,
        fx_rate=fx,
        amount_ghs=amount_ghs,
        rate_type=project.rate_type,
        source_rate_date=rate.rate_date,
    )
    db.add(invoice)
    project.next_invoice_date = next_date_for_recurrence(invoice_date, project.recurrence)
    db.commit()
    db.refresh(invoice)
    return invoice


def send_invoice_email(to_email: str, subject: str, body: str) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL", smtp_user or "noreply@example.com")

    if not smtp_host or not smtp_user or not smtp_password:
        raise ValueError("SMTP_HOST, SMTP_USER, SMTP_PASSWORD must be configured")

    message = EmailMessage()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(message)


def create_job_log(db: Session, job_name: str, status: str, message: str) -> None:
    db.add(JobLog(job_name=job_name, status=status, message=message[:500]))
    db.commit()
    level = "error" if status in {"failed"} else "info"
    log_event(level, "job_log", job_name=job_name, status=status, message=message[:500])
