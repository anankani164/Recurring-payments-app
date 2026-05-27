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
    amount_usd: float = Field(gt=0)
    recurrence: RecurrenceType = RecurrenceType.monthly
    rate_type: RateType = RateType.tts_selling
    next_invoice_date: date


class ProjectRead(BaseModel):
    id: int
    name: str
    client_id: int
    amount_usd: float
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
    model_config = {"from_attributes": True}


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
    email: EmailStr
    role: str
    is_active: bool
    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
