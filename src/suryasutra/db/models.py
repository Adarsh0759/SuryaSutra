"""SQLAlchemy ORM models (CLAUDE.md §9, D-18).

Scoped to the three tables needed to persist a triage run and its usage: `alarms`,
`triage_runs`, `usage`. `documents`/`chunks`/`requirements`/`feedback` stay file- and
config-based for now — ingestion doesn't write to a DB at all (the corpus is rebuilt
in-memory at process startup, D-15), and wiring that up is a separate, larger piece of
work, not pulled in here unasked.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Alarm(Base):
    __tablename__ = "alarms"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[str]
    inverter_id: Mapped[str]
    brand: Mapped[str]
    model: Mapped[str]
    code: Mapped[str]
    category: Mapped[str]
    message: Mapped[str]
    raised_at: Mapped[datetime]
    is_synthetic: Mapped[bool]
    # Eval ground truth (D-14) for synthetic alarms; null for real ones, where it's
    # genuinely unknown until someone investigates.
    answerable: Mapped[bool | None] = mapped_column(default=None)

    triage_runs: Mapped[list["TriageRun"]] = relationship(back_populates="alarm")


class TriageRun(Base):
    __tablename__ = "triage_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    alarm_id: Mapped[int] = mapped_column(ForeignKey("alarms.id"))
    method: Mapped[str]
    budget: Mapped[int]
    # Per-request citation ids actually used (e.g. ["c1", "c2"]) — the full detail
    # behind each one (page, text) lives in answer_json's "sources", not duplicated.
    selected_chunk_ids: Mapped[list[str]] = mapped_column(JSON)
    status: Mapped[str]  # "ANSWERED" | "INSUFFICIENT"
    missing_requirements: Mapped[list[str]] = mapped_column(JSON)
    answer_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    model: Mapped[str | None] = mapped_column(default=None)
    embedding_model: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime]

    alarm: Mapped["Alarm"] = relationship(back_populates="triage_runs")
    usage: Mapped["Usage | None"] = relationship(back_populates="run", uselist=False)


class Usage(Base):
    __tablename__ = "usage"

    run_id: Mapped[int] = mapped_column(ForeignKey("triage_runs.id"), primary_key=True)
    input_tokens: Mapped[int]
    output_tokens: Mapped[int]
    token_source: Mapped[str]  # "provider" | "estimate" (D-22)
    cost_inr: Mapped[float]
    latency_ms: Mapped[float | None] = mapped_column(default=None)

    run: Mapped["TriageRun"] = relationship(back_populates="usage")
