from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class RateType(str, Enum):
    cash_buying = "cash_buying"
    cash_selling = "cash_selling"
    tts_buying = "tts_buying"
    tts_selling = "tts_selling"


class RecurrenceType(str, Enum):
    monthly = "monthly"
    weekly = "weekly"
    biweekly = "biweekly"
    biannually = "biannually"


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr


class ClientRead(BaseModel):
    id: int
    name: str
    email: EmailStr
    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    client_id: int
    billing_currency: str = Field(default="USD", pattern="^(USD|GHS)$")
    amount_usd: float = Field(default=0.0, ge=0)
    amount_ghs: float | None = Field(default=None, gt=0)
    rate_source_url: HttpUrl | None = None
    recurrence: RecurrenceType = RecurrenceType.monthly
    rate_type: RateType = RateType.tts_selling
    next_invoice_date: date


class ProjectRead(BaseModel):
    id: int
    name: str
    client_id: int
    billing_currency: str
    amount_usd: float
    amount_ghs: float | None
    rate_source_url: str | None
    recurrence: str
    rate_type: str
    next_invoice_date: date
    model_config = {"from_attributes": True}


class FxRateCreate(BaseModel):
    rate_date: date
    code: str = Field(default="USD", min_length=3, max_length=10)
    cash_buying: float = Field(gt=0)
    cash_selling: float = Field(gt=0)
    tts_buying: float = Field(gt=0)
    tts_selling: float = Field(gt=0)
    source_url: HttpUrl


class FxRateRead(BaseModel):
    id: int
    rate_date: date
    code: str
    cash_buying: float
    cash_selling: float
    tts_buying: float
    tts_selling: float
    source_url: str
    model_config = {"from_attributes": True}


class InvoiceRead(BaseModel):
    id: int
    project_id: int
    invoice_date: date
    amount_usd: float
    fx_rate: float
    amount_ghs: float
    rate_type: str
    source_rate_date: date
    status: str
    rate_pdf_path: str | None
    model_config = {"from_attributes": True}


class InvoiceStatusUpdate(BaseModel):
    status: str = Field(pattern="^(pending|completed)$")


class ParsePdfRequest(BaseModel):
    source_url: HttpUrl
    target_code: str = Field(default="USD", min_length=3, max_length=10)


class ParsePdfResponse(BaseModel):
    rate_date: date
    code: str
    cash_buying: float
    cash_selling: float
    tts_buying: float
    tts_selling: float


class JobLogRead(BaseModel):
    id: int
    job_name: str
    status: str
    message: str
    created_at: datetime
    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="user")


class UserLogin(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=100)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = None
    is_active: bool | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
