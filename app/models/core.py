
import uuid
from datetime import datetime, timezone

from app.extensions import db


def new_id():
    return str(uuid.uuid4())


class Organisation(db.Model):
    __tablename__ = "organisations"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    name = db.Column(db.String(150), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(30), default="active", nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )


class Membership(db.Model):
    __tablename__ = "memberships"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    organisation_id = db.Column(
        db.String(36), db.ForeignKey("organisations.id"), nullable=False
    )
    role = db.Column(db.String(30), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "organisation_id"),
    )


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    organisation_id = db.Column(
        db.String(36), db.ForeignKey("organisations.id"), nullable=False
    )
    name = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(30), default="active", nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )


class ProjectMember(db.Model):
    __tablename__ = "project_members"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    project_id = db.Column(db.String(36), db.ForeignKey("projects.id"), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    permissions = db.Column(db.JSON, default=dict, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("project_id", "user_id"),
    )


class AuditEvent(db.Model):
    __tablename__ = "audit_events"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    organisation_id = db.Column(
        db.String(36), db.ForeignKey("organisations.id"), nullable=False
    )
    actor_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(80), nullable=False)
    resource_id = db.Column(db.String(36), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )



class Source(db.Model):
    __tablename__ = "sources"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    project_id = db.Column(
        db.String(36), db.ForeignKey("projects.id"), nullable=False, index=True
    )
    source_type = db.Column(db.String(40), nullable=False, default="manual_upload")
    name = db.Column(db.String(255), nullable=False)
    created_by = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    permissions = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    source_id = db.Column(
        db.String(36), db.ForeignKey("sources.id"), nullable=False, index=True
    )
    project_id = db.Column(
        db.String(36), db.ForeignKey("projects.id"), nullable=False, index=True
    )
    original_name = db.Column(db.String(255), nullable=False)
    storage_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    content_hash = db.Column(db.String(64), nullable=False)
    extracted_text = db.Column(db.Text, nullable=False)
    classification = db.Column(db.String(30), default="internal", nullable=False)
    status = db.Column(db.String(30), default="processed", nullable=False)
    uploaded_by = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint("project_id", "content_hash"),
    )


class DocumentChunk(db.Model):
    __tablename__ = "document_chunks"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    document_id = db.Column(
        db.String(36), db.ForeignKey("documents.id"), nullable=False, index=True
    )
    chunk_index = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)

    __table_args__ = (
        db.UniqueConstraint("document_id", "chunk_index"),
    )


class KnowledgeItem(db.Model):
    __tablename__ = "knowledge_items"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    project_id = db.Column(
        db.String(36), db.ForeignKey("projects.id"), nullable=False, index=True
    )
    document_id = db.Column(
        db.String(36), db.ForeignKey("documents.id"), nullable=False, index=True
    )
    chunk_id = db.Column(
        db.String(36), db.ForeignKey("document_chunks.id"), nullable=False, index=True
    )

    item_type = db.Column(db.String(40), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)

    # needs_review, approved, rejected
    status = db.Column(db.String(30), nullable=False, default="needs_review")

    # inferred, verified, conflicting, outdated, missing
    uncertainty = db.Column(db.String(30), nullable=False, default="inferred")

    evidence_text = db.Column(db.Text, nullable=False)
    evidence_location = db.Column(db.JSON, nullable=False, default=dict)

    extracted_by = db.Column(db.String(40), nullable=False, default="rules-v1")
    reviewed_by = db.Column(
        db.String(36), db.ForeignKey("users.id"), nullable=True
    )
    reviewed_at = db.Column(
        db.DateTime(timezone=True), nullable=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "chunk_id", "item_type", "title",
            name="uq_knowledge_chunk_type_title"
        ),
    )
