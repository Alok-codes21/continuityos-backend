"""Database schema. Mirrors the table list in the ContinuityOS product plan (section 10)."""
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import (Boolean, DateTime, ForeignKey, Integer, String, Text,
                        UniqueConstraint, Index, JSON)
from sqlalchemy.orm import Mapped, mapped_column

from .crypto import EncryptedText
from .db import Base


def uid(prefix="id"):
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def col_id(prefix):
    return mapped_column(String(40), primary_key=True, default=lambda: uid(prefix))


class Organisation(Base):
    __tablename__ = "organisations"
    id: Mapped[str] = col_id("org")
    name: Mapped[str] = mapped_column(String(200))
    domain: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = col_id("usr")
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(300))
    sessions_revoked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("org_id", "user_id"),)
    id: Mapped[str] = col_id("mem")
    org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # admin | manager | contributor | incoming


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = col_id("prj")
    org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id"),)
    id: Mapped[str] = col_id("pm")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="contributor")


class Integration(Base):
    __tablename__ = "integrations"
    id: Mapped[str] = col_id("int")
    org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), index=True)
    connector: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | revoked
    encrypted_token: Mapped[str] = mapped_column(Text, default="")
    scopes: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class IntegrationPermission(Base):
    __tablename__ = "integration_permissions"
    id: Mapped[str] = col_id("ip")
    integration_id: Mapped[str] = mapped_column(ForeignKey("integrations.id", ondelete="CASCADE"), index=True)
    scope: Mapped[str] = mapped_column(String(100))
    approved: Mapped[bool] = mapped_column(Boolean, default=True)


class SourceSelection(Base):
    """Selective ingestion: which repos/channels/folders are included or excluded."""
    __tablename__ = "source_selections"
    id: Mapped[str] = col_id("sel")
    integration_id: Mapped[str] = mapped_column(ForeignKey("integrations.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    source_ref: Mapped[str] = mapped_column(String(300))
    included: Mapped[bool] = mapped_column(Boolean, default=True)
    date_from: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    date_to: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    content_types: Mapped[list] = mapped_column(JSON, default=list)


class ConsentRecord(Base):
    __tablename__ = "consent_records"
    id: Mapped[str] = col_id("con")
    org_id: Mapped[str] = mapped_column(String(40), index=True)
    integration_id: Mapped[str] = mapped_column(String(40), nullable=True)
    user_id: Mapped[str] = mapped_column(String(40), nullable=True)  # individual consent, when applicable
    kind: Mapped[str] = mapped_column(String(30))  # organisation | individual
    granted: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (UniqueConstraint("project_id", "source_type", "external_id"),)
    id: Mapped[str] = col_id("src")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    integration_id: Mapped[str] = mapped_column(String(40), nullable=True)
    source_type: Mapped[str] = mapped_column(String(40))
    external_id: Mapped[str] = mapped_column(String(300))
    name: Mapped[str] = mapped_column(String(300))
    last_cursor: Mapped[str] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class SourceSyncJob(Base):
    __tablename__ = "source_sync_jobs"
    id: Mapped[str] = col_id("job")
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    source_id: Mapped[str] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    fetched: Mapped[int] = mapped_column(Integer, default=0)
    stored: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)
    redactions: Mapped[int] = mapped_column(Integer, default=0)
    flagged: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class SourceRecord(Base):
    __tablename__ = "source_records"
    __table_args__ = (UniqueConstraint("project_id", "content_hash"), Index("ix_rec_proj_type", "project_id", "record_type"))
    id: Mapped[str] = col_id("rec")
    org_id: Mapped[str] = mapped_column(String(40), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str] = mapped_column(String(40), nullable=True)
    source_type: Mapped[str] = mapped_column(String(40))
    external_id: Mapped[str] = mapped_column(String(300))
    record_type: Mapped[str] = mapped_column(String(40))  # commit | pull_request | issue | document | message
    title: Mapped[str] = mapped_column(String(500), default="")
    content: Mapped[str] = mapped_column(EncryptedText)
    author: Mapped[str] = mapped_column(String(200), nullable=True)
    url: Mapped[str] = mapped_column(String(500), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    content_hash: Mapped[str] = mapped_column(String(64))
    visibility: Mapped[str] = mapped_column(String(20), default="project")  # project | restricted
    redactions: Mapped[int] = mapped_column(Integer, default=0)
    injection_suspected: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_status: Mapped[str] = mapped_column(String(20), default="processed")
    version: Mapped[int] = mapped_column(Integer, default=1)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = col_id("doc")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    record_id: Mapped[str] = mapped_column(String(40), nullable=True)
    filename: Mapped[str] = mapped_column(String(300))
    mime_type: Mapped[str] = mapped_column(String(100))
    byte_size: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    uploaded_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[str] = col_id("chk")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    record_id: Mapped[str] = mapped_column(ForeignKey("source_records.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(EncryptedText)
    embedding: Mapped[list] = mapped_column(JSON, default=list)


class PeopleKnowledge(Base):
    __tablename__ = "people_knowledge"
    id: Mapped[str] = col_id("pk")
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    skill: Mapped[str] = mapped_column(String(100))
    level: Mapped[str] = mapped_column(String(20), default="working")
    source: Mapped[str] = mapped_column(String(30), default="self_reported")
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)  # prior systems, approaches, training needs, recommendations


class Component(Base):
    """APIs, services, databases, infrastructure units."""
    __tablename__ = "components"
    __table_args__ = (UniqueConstraint("project_id", "key"),)
    id: Mapped[str] = col_id("cmp")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(30), default="service")  # api | service | database | repo | module
    technologies: Mapped[list] = mapped_column(JSON, default=list)
    criticality: Mapped[str] = mapped_column(String(20), default="normal")


class Claim(Base):
    __tablename__ = "knowledge_claims"
    id: Mapped[str] = col_id("clm")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(30), index=True)  # decision, task, bug, risk, api, owner, dependency, procedure, question, ...
    subject_key: Mapped[str] = mapped_column(String(300), index=True)
    statement: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="inferred")
    # verified | evidence_backed | inferred | conflicting | missing | outdated | superseded
    freshness: Mapped[str] = mapped_column(String(20), default="current")  # current | stale | superseded | unknown
    superseded_by: Mapped[str] = mapped_column(String(40), nullable=True)
    created_by: Mapped[str] = mapped_column(String(40), default="system")
    verified_by: Mapped[str] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class EvidenceLink(Base):
    __tablename__ = "evidence_links"
    id: Mapped[str] = col_id("evd")
    claim_id: Mapped[str] = mapped_column(ForeignKey("knowledge_claims.id", ondelete="CASCADE"), index=True)
    record_id: Mapped[str] = mapped_column(String(40), nullable=True)
    excerpt: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(100), default="")
    quote_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    interview_response_id: Mapped[str] = mapped_column(String(40), nullable=True)


class KnowledgeEvent(Base):
    """Append-only continuity ledger. Corrections create new rows; rows are never updated or deleted by the API."""
    __tablename__ = "knowledge_events"
    id: Mapped[str] = col_id("evt")
    __table_args__ = (UniqueConstraint("project_id", "seq", name="uq_event_project_seq"),)
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    source_id: Mapped[str] = mapped_column(String(40), nullable=True)
    record_id: Mapped[str] = mapped_column(String(40), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    actor: Mapped[str] = mapped_column(String(200), nullable=True)
    event_type: Mapped[str] = mapped_column(String(40))
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str] = mapped_column(String(60))
    related_entities: Mapped[list] = mapped_column(JSON, default=list)
    previous_state: Mapped[dict] = mapped_column(JSON, nullable=True)
    new_state: Mapped[dict] = mapped_column(JSON, nullable=True)
    verification: Mapped[str] = mapped_column(String(20), default="inferred")
    permission: Mapped[str] = mapped_column(String(20), default="project")
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")


class GraphNode(Base):
    __tablename__ = "graph_nodes"
    __table_args__ = (UniqueConstraint("project_id", "node_type", "key"),)
    id: Mapped[str] = col_id("nd")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    node_type: Mapped[str] = mapped_column(String(30))
    key: Mapped[str] = mapped_column(String(300))
    name: Mapped[str] = mapped_column(String(300))
    props: Mapped[dict] = mapped_column(JSON, default=dict)
    user_id: Mapped[str] = mapped_column(String(40), nullable=True)


class GraphEdge(Base):
    __tablename__ = "dependencies"  # relationships between entities (plan: `dependencies`)
    __table_args__ = (UniqueConstraint("project_id", "src_id", "dst_id", "relation"),)
    id: Mapped[str] = col_id("edg")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    src_id: Mapped[str] = mapped_column(ForeignKey("graph_nodes.id", ondelete="CASCADE"), index=True)
    dst_id: Mapped[str] = mapped_column(ForeignKey("graph_nodes.id", ondelete="CASCADE"), index=True)
    relation: Mapped[str] = mapped_column(String(30))
    verification: Mapped[str] = mapped_column(String(20), default="inferred")
    record_id: Mapped[str] = mapped_column(String(40), nullable=True)
    claim_id: Mapped[str] = mapped_column(String(40), nullable=True)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = col_id("tsk")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    assignee_key: Mapped[str] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    record_id: Mapped[str] = mapped_column(String(40), nullable=True)


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[str] = col_id("dec")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    claim_id: Mapped[str] = mapped_column(String(40), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    decided_by: Mapped[str] = mapped_column(String(200), nullable=True)
    alternatives: Mapped[list] = mapped_column(JSON, default=list)
    rationale: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | superseded
    superseded_by: Mapped[str] = mapped_column(String(40), nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    record_id: Mapped[str] = mapped_column(String(40), nullable=True)


class KnowledgeGap(Base):
    __tablename__ = "knowledge_gaps"
    id: Mapped[str] = col_id("gap")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    gap_type: Mapped[str] = mapped_column(String(30))  # no_documented_owner | missing_procedure | undocumented_decision | unresolved_bug | unanswered_question
    entity_type: Mapped[str] = mapped_column(String(30), nullable=True)
    entity_key: Mapped[str] = mapped_column(String(300), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | resolved | unresolved_accepted
    found: Mapped[str] = mapped_column(Text, default="")
    recommended_action: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class RiskRecord(Base):
    __tablename__ = "risk_records"
    id: Mapped[str] = col_id("rsk")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    simulation_person_key: Mapped[str] = mapped_column(String(300), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    level: Mapped[str] = mapped_column(String(20))
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class HandoverInterview(Base):
    __tablename__ = "handover_interviews"
    id: Mapped[str] = col_id("ivw")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    person_key: Mapped[str] = mapped_column(String(300))
    person_user_id: Mapped[str] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | completed
    created_by: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    id: Mapped[str] = col_id("iq")
    interview_id: Mapped[str] = mapped_column(ForeignKey("handover_interviews.id", ondelete="CASCADE"), index=True)
    gap_id: Mapped[str] = mapped_column(String(40), nullable=True)
    parent_question_id: Mapped[str] = mapped_column(String(40), nullable=True)
    question: Mapped[str] = mapped_column(Text)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | answered | unresolved
    position: Mapped[int] = mapped_column(Integer, default=0)


class InterviewResponse(Base):
    __tablename__ = "interview_responses"
    id: Mapped[str] = col_id("irs")
    interview_id: Mapped[str] = mapped_column(ForeignKey("handover_interviews.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("interview_questions.id", ondelete="CASCADE"), index=True)
    answer: Mapped[str] = mapped_column(Text)
    claim_id: Mapped[str] = mapped_column(String(40), nullable=True)
    employee_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    manager_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = col_id("apr")
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(30))  # interview_response | correction | skill_profile | handover_doc | scope_change
    target_id: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | approved | rejected
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    requested_by: Mapped[str] = mapped_column(String(40))
    decided_by: Mapped[str] = mapped_column(String(40), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    decided_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class Handover(Base):
    __tablename__ = "handovers"
    id: Mapped[str] = col_id("hnd")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    departing_person_key: Mapped[str] = mapped_column(String(300))
    incoming_user_id: Mapped[str] = mapped_column(String(40), nullable=True)
    role_profile: Mapped[str] = mapped_column(String(30), default="backend")
    generated_by: Mapped[str] = mapped_column(String(40))
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class HandoverItem(Base):
    __tablename__ = "handover_items"
    id: Mapped[str] = col_id("hit")
    handover_id: Mapped[str] = mapped_column(ForeignKey("handovers.id", ondelete="CASCADE"), index=True)
    section: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="inferred")
    claim_id: Mapped[str] = mapped_column(String(40), nullable=True)
    evidence: Mapped[list] = mapped_column(JSON, default=list)


class RehearsalSession(Base):
    __tablename__ = "rehearsal_sessions"
    id: Mapped[str] = col_id("reh")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    turns: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = col_id("aud")
    org_id: Mapped[str] = mapped_column(String(40), index=True, nullable=True)
    project_id: Mapped[str] = mapped_column(String(40), nullable=True, index=True)
    actor_id: Mapped[str] = mapped_column(String(40), nullable=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    target_type: Mapped[str] = mapped_column(String(40), nullable=True)
    target_id: Mapped[str] = mapped_column(String(60), nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ContributorConsent(Base):
    """Individual consent: an author who withdraws consent has their contributions excluded and removed."""
    __tablename__ = "contributor_consents"
    __table_args__ = (UniqueConstraint("project_id", "author"),)
    id: Mapped[str] = col_id("ccn")
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    author: Mapped[str] = mapped_column(String(200))
    granted: Mapped[bool] = mapped_column(Boolean, default=True)
    decided_by: Mapped[str] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
