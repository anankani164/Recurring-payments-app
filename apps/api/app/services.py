import os
import smtplib
from datetime import date
from email.message import EmailMessage

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import FxRate, Invoice, JobLog, Project
from .observability import log_event

PDF_RATES_DIR = os.getenv("PDF_RATES_DIR", "/app/rate_pdfs")


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
    if recurrence == "biweekly":
        return current_date + relativedelta(weeks=2)
    if recurrence == "monthly":
        return current_date + relativedelta(months=1)
    if recurrence == "biannually":
        return current_date + relativedelta(months=6)
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


def generate_invoice_for_project(db: Session, project, invoice_date: date) -> object:
    existing = db.execute(
        select(Invoice).where(Invoice.project_id == project.id, Invoice.invoice_date == invoice_date)
    ).scalars().first()
    if existing:
        return existing

    rate_pdf_path: str | None = None

    if project.billing_currency == "GHS":
        # Fixed GHS amount — no FX lookup needed
        if not project.amount_ghs:
            raise ValueError("amount_ghs is required for GHS-billed projects")
        amount_ghs = project.amount_ghs
        fx = 1.0
        source_rate_date = invoice_date
    else:
        # USD billing — resolve or auto-fetch FX rate
        if project.rate_source_url:
            # Try to auto-fetch from the project's PDF URL
            try:
                from .pdf_rates import fetch_and_save_pdf, _parse_from_path, PdfParseError
                import tempfile
                from pathlib import Path
                from sqlalchemy.exc import IntegrityError as _IE
                from .models import FxRate as _FxR

                pdf_bytes, saved_path = fetch_and_save_pdf(project.rate_source_url, PDF_RATES_DIR)
                rate_pdf_path = saved_path

                # Parse and upsert the rate
                with tempfile.NamedTemporaryFile(prefix="fx_auto_", suffix=".pdf", delete=False) as tmp:
                    tmp.write(pdf_bytes)
                    tmp_path = Path(tmp.name)
                try:
                    parsed = _parse_from_path(tmp_path, "USD")
                finally:
                    tmp_path.unlink(missing_ok=True)

                new_rate = _FxR(source_url=project.rate_source_url, **parsed)
                db.add(new_rate)
                try:
                    db.commit()
                    db.refresh(new_rate)
                    fetched_rate = new_rate
                except _IE:
                    db.rollback()
                    # Rate already exists for that date — fetch it
                    fetched_rate = db.execute(
                        select(_FxR).where(_FxR.rate_date == parsed["rate_date"], _FxR.code == "USD")
                    ).scalars().first() or resolve_rate_for_date(db, invoice_date)

                rate = fetched_rate
            except Exception:  # noqa: BLE001
                # Fall back to most recent stored rate
                rate = resolve_rate_for_date(db, invoice_date)
        else:
            rate = resolve_rate_for_date(db, invoice_date)

        fx = get_rate_value(rate, project.rate_type)
        amount_ghs = round(project.amount_usd * fx, 2)
        source_rate_date = rate.rate_date

    invoice = Invoice(
        project_id=project.id,
        invoice_date=invoice_date,
        amount_usd=project.amount_usd if project.billing_currency == "USD" else 0.0,
        fx_rate=fx,
        amount_ghs=amount_ghs,
        rate_type=project.rate_type if project.billing_currency == "USD" else "fixed_ghs",
        source_rate_date=source_rate_date,
        status="pending",
        rate_pdf_path=rate_pdf_path,
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


def cleanup_old_rate_pdfs(max_age_days: int = 90) -> int:
    """Delete rate PDF files older than max_age_days. Returns count deleted."""
    import os
    from datetime import datetime, timedelta

    pdf_dir = os.getenv("PDF_RATES_DIR", "/app/rate_pdfs")
    if not os.path.isdir(pdf_dir):
        return 0
    cutoff = datetime.utcnow() - timedelta(days=max_age_days)
    deleted = 0
    for fname in os.listdir(pdf_dir):
        if not fname.endswith(".pdf"):
            continue
        fpath = os.path.join(pdf_dir, fname)
        try:
            mtime = datetime.utcfromtimestamp(os.path.getmtime(fpath))
            if mtime < cutoff:
                os.remove(fpath)
                deleted += 1
        except OSError:
            pass
    return deleted
