"""Recurring payments worker.

Run as a dedicated Railway service (cron or persistent worker process).
"""

import os
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

API_DIR = Path(__file__).resolve().parents[1] / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.models import Client, Project  # noqa: E402
from app.services import create_job_log, generate_invoice_for_project, send_invoice_email  # noqa: E402

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./recurring.db")


def run_daily_invoicing(run_date: date | None = None) -> int:
    run_date = run_date or date.today()
    generated = 0
    engine = create_engine(DATABASE_URL, future=True)
    with Session(engine) as db:
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
                generated += 1
                print(f"Generated invoice for project={project.id} on {run_date.isoformat()}")
            except Exception as exc:  # noqa: BLE001
                create_job_log(db, "invoice_generation", "failed", f"project_id={project.id}: {exc}")
    return generated


if __name__ == "__main__":
    total = run_daily_invoicing()
    print(f"Total invoices generated: {total}")
