"""Pydantic schemas for API contracts."""
from __future__ import annotations

from datetime import date as _dt_date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth ----
class RegisterIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)
    name: str = ""


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORMModel):
    id: str
    email: str
    name: str
    role: str


# ---- clients ----
class ClientIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    company: str = ""
    status: str = "active"
    email: str = ""
    phone: str = ""
    address: str = ""
    payment_terms: str = ""
    contract_notes: str = ""
    notes: str = ""


class ClientOut(ORMModel):
    id: str
    name: str
    company: str
    status: str
    email: str
    phone: str
    address: str
    payment_terms: str
    contract_notes: str
    notes: str
    created_at: datetime
    updated_at: datetime


# ---- projects ----
class MilestoneIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_date: _dt_date | None = None
    status: str = "todo"


class MilestoneOut(ORMModel):
    id: str
    project_id: str
    title: str
    due_date: _dt_date | None
    status: str


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    client_id: str | None = None
    status: str = "active"
    priority: str = "medium"
    start_date: _dt_date | None = None
    deadline: _dt_date | None = None
    progress: float = Field(default=0, ge=0, le=100)
    notes: str = ""


class ProjectOut(ORMModel):
    id: str
    name: str
    description: str
    client_id: str | None
    status: str
    priority: str
    start_date: _dt_date | None
    deadline: _dt_date | None
    progress: float
    notes: str
    client_name: str | None = None
    created_at: datetime
    updated_at: datetime


# ---- tasks ----
class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    priority: str = "medium"
    status: str = "todo"
    project_id: str | None = None
    client_id: str | None = None
    start_date: _dt_date | None = None
    due_date: _dt_date | None = None
    recurrence: str = ""


class TaskOut(ORMModel):
    id: str
    title: str
    description: str
    priority: str
    status: str
    project_id: str | None
    client_id: str | None
    start_date: _dt_date | None
    due_date: _dt_date | None
    completed_at: datetime | None
    recurrence: str
    created_at: datetime
    updated_at: datetime
    project_name: str | None = None
    client_name: str | None = None


# ---- meetings ----
class MeetingIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    client_id: str | None = None
    project_id: str | None = None
    scheduled_at: datetime | None = None
    summary: str = ""
    outcome: str = ""


# ---- knowledge ----
class NoteCreateIn(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    frontmatter: dict = Field(default_factory=dict)
    body: str = ""


class NoteUpdateIn(BaseModel):
    frontmatter: dict | None = None
    body: str | None = None


class NoteOut(BaseModel):
    path: str
    title: str
    body: str = ""
    frontmatter: dict = Field(default_factory=dict)
    links: list[str] = Field(default_factory=list)
    updated_at: float | None = None


# ---- daily notes ----
class DailyNoteIn(BaseModel):
    date: _dt_date | None = None  # defaults to today
    title: str = ""
    body: str = ""


# ---- content ----
class ContentIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    platform: str = "linkedin"
    format: str = "post"
    status: str = "idea"
    body: str = ""
    scheduled_for: datetime | None = None
    published_url: str = ""
    performance: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    notes: str = ""


# ---- finance ----
class TransactionIn(BaseModel):
    kind: str = Field(pattern="^(income|expense)$")
    amount: float = Field(gt=0, le=1_000_000_000)
    currency: str = "USD"
    category: str = ""
    client_id: str | None = None
    project_id: str | None = None
    date: _dt_date | None = None
    description: str = ""


class TransactionOut(ORMModel):
    id: str
    kind: str
    amount: float
    currency: str
    category: str
    client_id: str | None
    project_id: str | None
    date: date
    description: str
    created_at: datetime


class InvoiceIn(BaseModel):
    number: str = Field(min_length=1, max_length=64)
    client_id: str | None = None
    amount: float = Field(gt=0, le=1_000_000_000)
    currency: str = "USD"
    due_date: _dt_date | None = None
    status: str = "draft"
    paid_date: _dt_date | None = None
    description: str = ""


# ---- research ----
class ResearchIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    source_urls: list[str] = Field(default_factory=list)
    summary: str = ""
    tags: list[str] = Field(default_factory=list)
    related_projects: list[str] = Field(default_factory=list)
    created_from: str = "manual"


# ---- reports ----
class ReportOut(ORMModel):
    id: str
    type: str
    title: str
    body: str
    source: dict
    agent: str
    created_at: datetime


# ---- ai ----
class AgentRunIn(BaseModel):
    input: dict = Field(default_factory=dict)
    question: str = ""


class ApprovalResolveIn(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    reason: str = ""


# ---- automation ----
class TriggerIn(BaseModel):
    payload: dict = Field(default_factory=dict)


# ---- queue ----
class QueueIn(BaseModel):
    type: str = Field(pattern="^(content-draft|project-analysis|meeting-prep|weekly-review|daily-brief)$")
    description: str = ""
    input: dict = Field(default_factory=dict)
    priority: str = "normal"
