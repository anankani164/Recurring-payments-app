from contextlib import asynccontextmanager
from datetime import date
from datetime import datetime, timedelta
import os
from pathlib import Path
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import (
    create_access_token,
    hash_password,
    require_admin_user,
    require_current_user,
    require_superadmin_user,
    verify_password,
)
from .config import (
    ALERT_EMAIL,
    CORS_ORIGINS,
    ENABLE_ALERT_EMAILS,
    ENABLE_SCHEDULER,
    JSON_LOGS,
    SCHEDULER_INTERVAL_MINUTES,
    validate_runtime_config,
)
from .database import SessionLocal, get_db
from .models import Client, FxRate, Invoice, JobLog, Project, SchedulerLock, User
from .observability import configure_logging, log_event
from .pdf_rates import PdfParseError, parse_bank_pdf_rates, parse_uploaded_pdf
from .schemas import (
    ClientCreate,
    ClientRead,
    FxRateCreate,
    FxRateRead,
    InvoiceRead,
    InvoiceStatusUpdate,
    JobLogRead,
    ParsePdfRequest,
    ParsePdfResponse,
    ProjectCreate,
    ProjectRead,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserRead,
    UserUpdate,
)
from .services import cleanup_old_rate_pdfs, create_job_log, generate_invoice_for_project, send_invoice_email

scheduler = BackgroundScheduler()


def acquire_distributed_lock(db: Session, name: str, owner_id: str, ttl_minutes: int = 30) -> bool:
    now = datetime.utcnow()
    lock = db.execute(select(SchedulerLock).where(SchedulerLock.name == name)).scalars().first()
    if lock and lock.expires_at > now:
        return False
    if lock:
        lock.owner_id = owner_id
        lock.expires_at = now + timedelta(minutes=ttl_minutes)
    else:
        db.add(SchedulerLock(name=name, owner_id=owner_id, expires_at=now + timedelta(minutes=ttl_minutes)))
    db.commit()
    return True


def release_distributed_lock(db: Session, name: str, owner_id: str) -> None:
    lock = db.execute(select(SchedulerLock).where(SchedulerLock.name == name)).scalars().first()
    if lock and lock.owner_id == owner_id:
        db.delete(lock)
        db.commit()


def run_embedded_worker() -> None:
    owner_id = f"worker-{uuid4().hex[:10]}"
    lock_name = "embedded_worker"

    run_date = date.today()
    with SessionLocal() as db:
        if not acquire_distributed_lock(db, lock_name, owner_id):
            create_job_log(db, "embedded_worker", "skipped", "Run skipped due to active distributed lock")
            return

        try:
            create_job_log(db, "embedded_worker", "started", f"Run started for {run_date.isoformat()}")
            projects = db.execute(select(Project).where(Project.next_invoice_date <= run_date)).scalars().all()
            for project in projects:
                try:
                    invoice = generate_invoice_for_project(db, project, run_date)
                    client = db.get(Client, project.client_id)
                    if client:
                        try:
                            send_invoice_email(
                                to_email=client.email,
                                subject=f"Invoice ready: {project.name} ({invoice.invoice_date})",
                                body=(
                                    f"Project: {project.name}\n"
                                    f"USD Amount: {invoice.amount_usd}\n"
                                    f"Rate Type: {invoice.rate_type}\n"
                                    f"FX Rate: {invoice.fx_rate}\n"
                                    f"GHS Amount: {invoice.amount_ghs}\n"
                                ),
                            )
                            create_job_log(db, "invoice_email", "success", f"Sent invoice email to {client.email}")
                        except Exception as exc:  # noqa: BLE001
                            create_job_log(db, "invoice_email", "failed", str(exc))
                            if ENABLE_ALERT_EMAILS and ALERT_EMAIL:
                                try:
                                    send_invoice_email(
                                        to_email=ALERT_EMAIL,
                                        subject="Recurring Payments alert: invoice email failed",
                                        body=f"project_id={project.id}; client={client.email}; error={exc}",
                                    )
                                except Exception as alert_exc:  # noqa: BLE001
                                    create_job_log(db, "alert_email", "failed", str(alert_exc))
                except Exception as exc:  # noqa: BLE001
                    create_job_log(db, "invoice_generation", "failed", f"project_id={project.id}: {exc}")
                    if ENABLE_ALERT_EMAILS and ALERT_EMAIL:
                        try:
                            send_invoice_email(
                                to_email=ALERT_EMAIL,
                                subject="Recurring Payments alert: invoice generation failed",
                                body=f"project_id={project.id}; error={exc}",
                            )
                        except Exception as alert_exc:  # noqa: BLE001
                            create_job_log(db, "alert_email", "failed", str(alert_exc))

            create_job_log(db, "embedded_worker", "success", f"Run finished. projects_due={len(projects)}")
            cleaned = cleanup_old_rate_pdfs()
            if cleaned:
                create_job_log(db, "pdf_cleanup", "success", f"Deleted {cleaned} old rate PDFs")
        finally:
            release_distributed_lock(db, lock_name, owner_id)


def ensure_default_superadmin(db: Session) -> None:
    existing = db.execute(select(User).where(User.username == "superadmin")).scalars().first()
    if existing:
        return
    db.add(
        User(
            username="superadmin",
            email="superadmin@example.com",
            password_hash=hash_password("Nankani1"),
            role="superadmin",
        )
    )
    db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_runtime_config()
    configure_logging(JSON_LOGS)
    log_event("info", "app_startup", scheduler_enabled=ENABLE_SCHEDULER, scheduler_interval=SCHEDULER_INTERVAL_MINUTES)
    with SessionLocal() as db:
        ensure_default_superadmin(db)
    if ENABLE_SCHEDULER:
        scheduler.add_job(run_embedded_worker, "interval", minutes=SCHEDULER_INTERVAL_MINUTES, id="embedded_worker")
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Recurring Payments API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the embedded Next.js frontend if built files are present
_web_out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_out")
_next_static = os.path.join(_web_out, "_next")
if os.path.exists(_next_static):
    app.mount("/_next", StaticFiles(directory=_next_static), name="nextjs_assets")


@app.get("/")
def home():
    index = os.path.join(_web_out, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return HTMLResponse(f"<html><body><h1>Recurring Payments API v2</h1><p>web_out not found at: {_web_out}</p><p><a href='/docs'>API Docs</a></p></body></html>")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "single_service_mode": True,
        "scheduler_enabled": ENABLE_SCHEDULER,
        "scheduler_interval_minutes": SCHEDULER_INTERVAL_MINUTES,
    }


@app.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_superadmin_user)])
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.execute(select(User).where((User.email == payload.email) | (User.username == payload.username))).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    if payload.role not in {"admin", "user"}:
        raise HTTPException(status_code=422, detail="Role must be admin or user")
    user = User(username=payload.username, email=payload.email, password_hash=hash_password(payload.password), role=payload.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/users", response_model=list[UserRead], dependencies=[Depends(require_superadmin_user)])
def list_users(db: Session = Depends(get_db)):
    return db.execute(select(User).order_by(User.created_at.desc())).scalars().all()


@app.patch("/users/{user_id}", response_model=UserRead, dependencies=[Depends(require_superadmin_user)])
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.username == "superadmin" and payload.is_active is False:
        raise HTTPException(status_code=400, detail="Cannot deactivate superadmin")
    if payload.username is not None:
        conflict = db.execute(select(User).where(User.username == payload.username)).scalars().first()
        if conflict and conflict.id != user_id:
            raise HTTPException(status_code=409, detail="Username already taken")
        user.username = payload.username
    if payload.email is not None:
        conflict = db.execute(select(User).where(User.email == payload.email)).scalars().first()
        if conflict and conflict.id != user_id:
            raise HTTPException(status_code=409, detail="Email already taken")
        user.email = payload.email
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.role is not None:
        if payload.role not in {"admin", "user", "superadmin"}:
            raise HTTPException(status_code=422, detail="Invalid role")
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=TokenResponse)
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.username == payload.username)).scalars().first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is deactivated")
    return TokenResponse(access_token=create_access_token(user.username, user.role))

# existing endpoints
@app.post("/clients", response_model=ClientRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin_user)])
def create_client(payload: ClientCreate, db: Session = Depends(get_db)):
    client = Client(name=payload.name, email=payload.email)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client

@app.get("/clients", response_model=list[ClientRead], dependencies=[Depends(require_current_user)])
def list_clients(db: Session = Depends(get_db)):
    return db.execute(select(Client).order_by(Client.created_at.desc())).scalars().all()

@app.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin_user)])
def delete_client(client_id: int, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(client)
    db.commit()

@app.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin_user)])
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    client = db.get(Client, payload.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    data = payload.model_dump()
    if data.get('rate_source_url') is not None:
        data['rate_source_url'] = str(data['rate_source_url'])
    project = Project(**data)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@app.get("/projects", response_model=list[ProjectRead], dependencies=[Depends(require_current_user)])
def list_projects(db: Session = Depends(get_db)):
    return db.execute(select(Project).order_by(Project.next_invoice_date.asc())).scalars().all()

@app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin_user)])
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()

@app.post("/rates", response_model=FxRateRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin_user)])
def create_rate(payload: FxRateCreate, db: Session = Depends(get_db)):
    rate = FxRate(**payload.model_dump())
    db.add(rate)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Rate for this date/code already exists") from exc
    db.refresh(rate)
    return rate

@app.get("/rates", response_model=list[FxRateRead], dependencies=[Depends(require_current_user)])
def list_rates(db: Session = Depends(get_db)):
    return db.execute(select(FxRate).order_by(FxRate.rate_date.desc())).scalars().all()

@app.delete("/rates/{rate_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin_user)])
def delete_rate(rate_id: int, db: Session = Depends(get_db)):
    rate = db.get(FxRate, rate_id)
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")
    db.delete(rate)
    db.commit()

@app.post("/rates/parse-pdf", response_model=ParsePdfResponse, dependencies=[Depends(require_current_user)])
def parse_pdf_rates(payload: ParsePdfRequest):
    try:
        parsed = parse_bank_pdf_rates(str(payload.source_url), payload.target_code)
    except PdfParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ParsePdfResponse(**parsed)

@app.post("/rates/ingest-pdf", response_model=FxRateRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin_user)])
def ingest_pdf_rates(payload: ParsePdfRequest, db: Session = Depends(get_db)):
    try:
        parsed = parse_bank_pdf_rates(str(payload.source_url), payload.target_code)
    except PdfParseError as exc:
        create_job_log(db, "pdf_ingestion", "failed", str(exc))
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    rate = FxRate(source_url=str(payload.source_url), **parsed)
    db.add(rate)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Rate for this date/code already exists") from exc
    db.refresh(rate)
    create_job_log(db, "pdf_ingestion", "success", f"Ingested {rate.code} {rate.rate_date}")
    return rate

@app.post("/rates/upload-pdf", response_model=FxRateRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin_user)])
async def upload_pdf_rates(
    file: UploadFile = File(...),
    target_code: str = Form(default="USD"),
    db: Session = Depends(get_db),
):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are accepted")
    pdf_bytes = await file.read()
    try:
        parsed = parse_uploaded_pdf(pdf_bytes, target_code)
    except PdfParseError as exc:
        create_job_log(db, "pdf_upload", "failed", str(exc))
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    rate = FxRate(source_url=f"upload:{file.filename}", **parsed)
    db.add(rate)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Rate for this date/code already exists") from exc
    db.refresh(rate)
    create_job_log(db, "pdf_upload", "success", f"Uploaded {rate.code} {rate.rate_date}")
    return rate

@app.post('/run-jobs-now', dependencies=[Depends(require_admin_user)])
def run_jobs_now():
    run_embedded_worker()
    return {'status': 'ok'}

@app.post("/projects/{project_id}/invoice", response_model=InvoiceRead, dependencies=[Depends(require_admin_user)])
def create_invoice(project_id: int, invoice_date: date = Query(...), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return generate_invoice_for_project(db, project, invoice_date)

@app.get("/invoices", response_model=list[InvoiceRead], dependencies=[Depends(require_current_user)])
def list_invoices(db: Session = Depends(get_db)):
    return db.execute(select(Invoice).order_by(Invoice.invoice_date.desc())).scalars().all()

@app.get("/jobs", response_model=list[JobLogRead], dependencies=[Depends(require_admin_user)])
def list_job_logs(db: Session = Depends(get_db)):
    return db.execute(select(JobLog).order_by(JobLog.created_at.desc())).scalars().all()

@app.patch("/invoices/{invoice_id}/status", response_model=InvoiceRead, dependencies=[Depends(require_admin_user)])
def update_invoice_status(invoice_id: int, payload: InvoiceStatusUpdate, db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice.status = payload.status
    db.commit()
    db.refresh(invoice)
    return invoice

@app.get("/invoices/{invoice_id}/rate-pdf", dependencies=[Depends(require_current_user)])
def download_invoice_rate_pdf(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice or not invoice.rate_pdf_path:
        raise HTTPException(status_code=404, detail="No rate PDF for this invoice")
    if not os.path.exists(invoice.rate_pdf_path):
        raise HTTPException(status_code=404, detail="Rate PDF file not found on disk")
    return FileResponse(
        invoice.rate_pdf_path,
        media_type="application/pdf",
        filename=f"rate_proof_{invoice.invoice_date}.pdf",
    )
