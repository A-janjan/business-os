"""Normalized database models.

Authoritative sources:
- Structured, transactional entities (users, clients, projects, tasks,
  transactions, invoices, executions, approvals, queue requests, reports) live
  in PostgreSQL/SQLite.
- Long-form textual knowledge (notes, meeting write-ups, content drafts) lives
  in the Markdown vault; the database only mirrors lightweight metadata.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.sqlite import JSON

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )


def _id():
    return mapped_column(String(36), primary_key=True, default=_uuid, nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = _id()
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[str] = mapped_column(String(32), default="admin", nullable=False)


class Client(Base, TimestampMixin):
    __tablename__ = "clients"

    id = _id()
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)  # active|prospect|inactive|churned
    email: Mapped[str] = mapped_column(String(320), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    address: Mapped[str] = mapped_column(String(500), default="")
    payment_terms: Mapped[str] = mapped_column(String(200), default="")
    contract_notes: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    projects: Mapped[list["Project"]] = relationship(back_populates="client")
    tasks: Mapped[list["Task"]] = relationship(back_populates="client")
    transactions: Mapped[list["FinancialTransaction"]] = relationship(back_populates="client")


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id = _id()
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    client_id: Mapped[str | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)  # active|on_hold|completed|cancelled
    priority: Mapped[str] = mapped_column(String(16), default="medium")  # low|medium|high|critical
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    progress: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    notes: Mapped[str] = mapped_column(Text, default="")

    client: Mapped["Client | None"] = relationship(back_populates="projects")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project")
    milestones: Mapped[list["ProjectMilestone"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectMilestone(Base, TimestampMixin):
    __tablename__ = "project_milestones"

    id = _id()
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="todo")  # todo|done

    project: Mapped["Project"] = relationship(back_populates="milestones")


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id = _id()
    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(16), default="medium", index=True)  # low|medium|high|critical
    status: Mapped[str] = mapped_column(String(32), default="todo", index=True)  # todo|in_progress|blocked|done|archived
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    client_id: Mapped[str | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recurrence: Mapped[str] = mapped_column(String(32), default="")  # none|daily|weekly|monthly

    project: Mapped["Project | None"] = relationship(back_populates="tasks")
    client: Mapped["Client | None"] = relationship(back_populates="tasks")


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (UniqueConstraint("task_id", "depends_on_id", name="uq_task_dep"),)

    id = _id()
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    depends_on_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class Meeting(Base, TimestampMixin):
    __tablename__ = "meetings"

    id = _id()
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    client_id: Mapped[str | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    outcome: Mapped[str] = mapped_column(Text, default="")


class KnowledgeDocument(Base, TimestampMixin):
    """Mirror of a markdown file in the vault. Content lives in the file."""

    __tablename__ = "knowledge_documents"

    id = _id()
    path: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)  # relative path
    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    folder: Mapped[str] = mapped_column(String(200), default="", index=True)
    frontmatter: Mapped[dict] = mapped_column(JSON, default=dict)
    tags: Mapped[list] = mapped_column(JSON, default=list)


class DailyNote(Base, TimestampMixin):
    __tablename__ = "daily_notes"

    id = _id()
    date: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)  # YYYY-MM-DD
    title: Mapped[str] = mapped_column(String(300), default="")
    path: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)  # relative path


class ContentItem(Base, TimestampMixin):
    __tablename__ = "content_items"

    id = _id()
    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), default="linkedin")  # linkedin|blog|newsletter|article|twitter|other
    format: Mapped[str] = mapped_column(String(50), default="post")  # post|article|newsletter|thread|video-script
    status: Mapped[str] = mapped_column(String(32), default="idea", index=True)  # idea|draft|review|scheduled|published|archived
    body: Mapped[str] = mapped_column(Text, default="")
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_url: Mapped[str] = mapped_column(String(500), default="")
    performance: Mapped[dict] = mapped_column(JSON, default=dict)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")


class FinancialTransaction(Base, TimestampMixin):
    __tablename__ = "financial_transactions"

    id = _id()
    kind: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # income|expense
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(120), default="")
    client_id: Mapped[str | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    invoice_id: Mapped[str | None] = mapped_column(ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")

    client: Mapped["Client | None"] = relationship(back_populates="transactions")


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id = _id()
    number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    client_id: Mapped[str | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)  # draft|sent|paid|overdue|void
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")


class ResearchDocument(Base, TimestampMixin):
    __tablename__ = "research_documents"

    id = _id()
    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    source_urls: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    related_projects: Mapped[list] = mapped_column(JSON, default=list)  # project ids
    created_from: Mapped[str] = mapped_column(String(50), default="manual")  # manual|ai|import


class BusinessReport(Base, TimestampMixin):
    __tablename__ = "business_reports"

    id = _id()
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # weekly-review|daily-brief|financial|project-status|meeting-prep|quarterly
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[dict] = mapped_column(JSON, default=dict)
    agent: Mapped[str] = mapped_column(String(64), default="")


class AIExecution(Base, TimestampMixin):
    __tablename__ = "ai_executions"

    id = _id()
    agent: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)  # pending|success|failed|awaiting_approval
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(64), default="")
    model: Mapped[str] = mapped_column(String(200), default="")
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")


class ApprovalRequest(Base, TimestampMixin):
    __tablename__ = "approval_requests"

    id = _id()
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)  # pending|approved|rejected
    reason: Mapped[str] = mapped_column(Text, default="")


class AutomationWorkflow(Base, TimestampMixin):
    __tablename__ = "automation_workflows"

    id = _id()
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(32), default="disabled")  # enabled|disabled|draft
    schedule: Mapped[str] = mapped_column(String(120), default="")


class AutomationExecution(Base, TimestampMixin):
    __tablename__ = "automation_executions"

    id = _id()
    workflow_id: Mapped[str] = mapped_column(ForeignKey("automation_workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)  # queued|running|success|failed
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    idem_key: Mapped[str] = mapped_column(String(200), unique=True, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = _id()
    actor: Mapped[str] = mapped_column(String(64), default="system")  # user|ai|system|automation
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), default="")
    entity_id: Mapped[str] = mapped_column(String(36), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


class QueueRequest(Base, TimestampMixin):
    __tablename__ = "queue_requests"

    id = _id()
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # content-draft|project-analysis|meeting-prep|weekly-review|daily-brief
    description: Mapped[str] = mapped_column(Text, default="")
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    priority: Mapped[str] = mapped_column(String(16), default="normal")  # low|normal|high
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    # pending|validating|processing|awaiting_approval|completed|failed|cancelled|requires_review
    error: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[dict] = mapped_column(JSON, default=dict)


class KnowledgeSource(Base, TimestampMixin):
    """Index of the markdown vault (mirror of files)."""

    __tablename__ = "knowledge_sources"

    id = _id()
    rel_path: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    folder: Mapped[str] = mapped_column(String(200), default="")
    modified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


Index("ix_tasks_status_due", Task.status, Task.due_date)
Index("ix_invoices_status_due", Invoice.status, Invoice.due_date)
Index("ix_transactions_date_kind", FinancialTransaction.date, FinancialTransaction.kind)
