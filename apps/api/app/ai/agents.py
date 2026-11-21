"""Agent registry, executor, structured-output validation.

Agents are thin coordination layers: prompts + output schemas + context.
No agent is a large autonomous loop; each run is one (or a few) validated
LLM calls. Deterministic work happens in plain service functions.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError

from ..securityutil import clamp_str


class AgentOutputError(RuntimeError):
    pass


# ---- structured outputs -----------------------------------------------------
class ExecutiveAssistantOut(BaseModel):
    summary: str = ""
    recommendations: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class BusinessAnalystOut(BaseModel):
    health: str = ""
    insights: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ProjectManagerOut(BaseModel):
    status: str = ""
    blockers: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class ClientIntelligenceOut(BaseModel):
    summary: str = ""
    commitments_outstanding: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)


class ContentOut(BaseModel):
    title: str = ""
    body: str = ""
    platform: str = "linkedin"
    rationale: str = ""


class FinancialAnalystOut(BaseModel):
    summary: str = ""
    trends: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)


class ResearchOut(BaseModel):
    summary: str = ""
    brief: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


# ---- agent specs -------------------------------------------------------------
@dataclass(frozen=True)
class AgentSpec:
    name: str
    role: str
    description: str
    system_prompt: str
    output_model: type[BaseModel]
    requires_approval: bool = False


_SYS_EXEC = """You are the Executive Assistant for a one-person business operating leverage through a Business OS.
You have access to the business context below. Answer the user's question using ONLY that context and your general knowledge clearly separated.
Never invent facts: if a number or date is not in the context, say so. Respond with JSON matching the schema."""

_SYS_BA = """You are the Business Analyst for a one-person business. Analyze the business context below.
Be specific and evidence-based; every claim must trace to the provided context. Respond with JSON matching the schema."""

_SYS_PM = """You are the Project Manager agent. Assess the given project(s) using ONLY the provided data.
Never claim progress or deadlines that are not in the context. Respond with JSON matching the schema."""

_SYS_CI = """You are the Client Intelligence agent. Summarize the client's relationship using ONLY the provided data.
Flag outstanding commitments, tone down certainty, and never invent communications that were not recorded. Respond with JSON matching the schema."""

_SYS_CONTENT = """You are the Content agent. Produce a high-quality draft in the requested format.
Do not fabricate statistics, client names, or events. Research notes and context provided are the only source of facts.
Respond with JSON matching the schema. The draft body will be reviewed by a human before publication."""

_SYS_FA = """You are the Financial Analyst agent. Analyze the financial context below.
Only use the figures provided. Never treat estimates as facts. Respond with JSON matching the schema."""

_SYS_RESEARCH = """You are the Research agent. Produce a source-linked brief from the provided research and context.
Never fabricate sources. If sources are not provided, say so explicitly and provide a clearly labeled internal summary only.
Respond with JSON matching the schema."""

AGENTS: dict[str, AgentSpec] = {spec.name: spec for spec in [
    AgentSpec(
        name="executive-assistant",
        role="Executive Assistant",
        description="Primary user-facing agent: context retrieval, delegation, actionable answers.",
        system_prompt=_SYS_EXEC,
        output_model=ExecutiveAssistantOut,
    ),
    AgentSpec(
        name="business-analyst",
        role="Business Analyst",
        description="Business health, strategic insights, opportunities, risks.",
        system_prompt=_SYS_BA,
        output_model=BusinessAnalystOut,
    ),
    AgentSpec(
        name="project-manager",
        role="Project Manager",
        description="Project progress, blockers, deadline risks, next actions.",
        system_prompt=_SYS_PM,
        output_model=ProjectManagerOut,
    ),
    AgentSpec(
        name="client-intelligence",
        role="Client Intelligence",
        description="Client summaries, outstanding commitments, follow-up recommendations.",
        system_prompt=_SYS_CI,
        output_model=ClientIntelligenceOut,
    ),
    AgentSpec(
        name="content",
        role="Content",
        description="Content ideas, briefs, drafts. Drafts are reviewed by a human before publication.",
        system_prompt=_SYS_CONTENT,
        output_model=ContentOut,
        requires_approval=True,
    ),
    AgentSpec(
        name="financial-analyst",
        role="Financial Analyst",
        description="Revenue, expense, invoice and trend analysis.",
        system_prompt=_SYS_FA,
        output_model=FinancialAnalystOut,
    ),
    AgentSpec(
        name="research",
        role="Research",
        description="Research briefs, competitor and market intelligence.",
        system_prompt=_SYS_RESEARCH,
        output_model=ResearchOut,
    ),
]}


def list_agents() -> list[dict]:
    return [
        {
            "name": spec.name,
            "role": spec.role,
            "description": spec.description,
            "requires_approval": spec.requires_approval,
        }
        for spec in AGENTS.values()
    ]


def get_agent_spec(name: str) -> AgentSpec | None:
    return AGENTS.get(name)


# ---- executor ----------------------------------------------------------------
@dataclass
class ExecutionResult:
    agent: str
    status: str  # success | failed
    output: str
    output_model: str
    duration_ms: int
    tokens_in: int
    tokens_out: int
    tokens_out_model: str = ""
    error: str = ""
    raw: dict = field(default_factory=dict)


class AgentExecutor:
    """Runs a registered agent against a configured provider."""

    def __init__(self, provider, *, temperature: float = 0.4, max_tokens: int = 4096):
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def run(
        self,
        name: str,
        input: dict[str, Any],
        question: str = "",
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        spec = get_agent_spec(name)
        if spec is None:
            raise AgentOutputError(f"unknown agent: {name}")
        started = time.time()

        context = context or {}
        schema_hint = json.dumps(spec.output_model.model_json_schema(), indent=2)
        user_prompt = (
            f"BUSINESS CONTEXT (JSON):\n{json.dumps(context, indent=2, default=str)[:12000]}\n\n"
            f"USER INPUT:\n{json.dumps(input, indent=2, default=str)[:4000]}\n\n"
            f"QUESTION/REQUEST:\n{question or input.get('question', '')}\n\n"
            "Respond with a single JSON object matching this schema:\n"
            f"{schema_hint}\n\n"
            "Do not add text outside the JSON object."
        )

        try:
            result = await self.provider.complete(
                spec.system_prompt,
                user_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                json_mode=True,
            )
        except Exception as exc:
            return ExecutionResult(
                agent=name, status="failed", output="", output_model=spec.output_model.__name__,
                duration_ms=int((time.time() - started) * 1000), tokens_in=0, tokens_out=0,
                error=str(exc),
            )

        parsed: dict | None = None
        error = ""
        try:
            parsed = _extract_json(result.text)
            spec.output_model.model_validate(parsed)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            error = f"output validation failed: {exc}"
            parsed = None

        return ExecutionResult(
            agent=name,
            status="success" if parsed is not None else "failed",
            output=json.dumps(parsed) if parsed else "",
            output_model=spec.output_model.__name__,
            duration_ms=int((time.time() - started) * 1000),
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            tokens_out_model=result.model,
            error=error,
            raw={"provider": result.provider, "model": result.model},
        )


def _extract_json(text: str) -> dict:
    """Parse a JSON object from model output; tolerate fences and noise."""
    if not text:
        raise ValueError("empty output")
    text = text.strip()
    if text.startswith("```"):
        # strip markdown fences
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start:end + 1])
    raise ValueError("no JSON object found in output")


# ---- approval helpers ------------------------------------------------
ApprovalCallback = Callable[[str, dict], Any]
