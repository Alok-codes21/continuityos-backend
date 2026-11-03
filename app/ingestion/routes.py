
import hashlib
import os
import uuid
from pathlib import Path

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from sqlalchemy import select

from app.extensions import db
from app.models import (
    Project,
    ProjectMember,
    Membership,
    Source,
    Document,
    DocumentChunk,
    AuditEvent,
)
from app.ingestion.processor import extract_text, split_into_chunks


ingestion_bp = Blueprint(
    "ingestion", __name__, url_prefix="/api/projects"
)

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv"}


def get_project_access(project_id):
    claims = get_jwt()
    user_id = get_jwt_identity()
    organisation_id = claims.get("organisation_id")

    project = db.session.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.organisation_id == organisation_id
        )
    )

    if not project:
        return None, None, (jsonify({"error": "Project not found."}), 404)

    membership = db.session.scalar(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.organisation_id == organisation_id
        )
    )

    project_member = db.session.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        )
    )

    if not membership:
        return None, None, (jsonify({"error": "Access denied."}), 403)

    if membership.role not in {"admin", "manager"} and not project_member:
        return None, None, (jsonify({"error": "Access denied."}), 403)

    return project, project_member, None


@ingestion_bp.post("/<project_id>/sources/upload")
@jwt_required()
def upload_document(project_id):
    project, project_member, error = get_project_access(project_id)

    if error:
        return error

    claims = get_jwt()
    user_id = get_jwt_identity()

    if project_member:
        permissions = project_member.permissions or {}
        if not permissions.get("can_upload", False):
            return jsonify({"error": "Upload permission denied."}), 403

    uploaded_file = request.files.get("file")

    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"error": "Select a file to upload."}), 400

    original_name = Path(uploaded_file.filename).name
    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": "Only PDF, DOCX, TXT and CSV files are supported."
        }), 415

    file_bytes = uploaded_file.stream.read(MAX_FILE_SIZE + 1)

    if not file_bytes:
        return jsonify({"error": "The selected file is empty."}), 400

    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({"error": "Maximum file size is 10 MB."}), 413

    content_hash = hashlib.sha256(file_bytes).hexdigest()

    existing = db.session.scalar(
        select(Document).where(
            Document.project_id == project_id,
            Document.content_hash == content_hash
        )
    )

    if existing:
        return jsonify({
            "error": "This file already exists in the project.",
            "document_id": existing.id
        }), 409

    try:
        extracted_text = extract_text(file_bytes, original_name)
        chunks = split_into_chunks(extracted_text)

        if not chunks:
            return jsonify({"error": "No usable text was extracted."}), 422

    except (ValueError, UnicodeDecodeError) as exc:
        return jsonify({"error": str(exc)}), 422

    except Exception:
        current_app.logger.exception("Document extraction failed")
        return jsonify({"error": "Could not process this document."}), 422

    storage_name = f"{uuid.uuid4().hex}{extension}"
    upload_directory = os.path.join(
        current_app.instance_path, "uploads"
    )

    os.makedirs(upload_directory, exist_ok=True)

    storage_path = os.path.join(upload_directory, storage_name)

    try:
        with open(storage_path, "xb") as stored_file:
            stored_file.write(file_bytes)

        source = Source(
            project_id=project.id,
            source_type="manual_upload",
            name=original_name,
            created_by=user_id,
            permissions={
                "organisation_id": project.organisation_id,
                "project_id": project.id
            }
        )

        db.session.add(source)
        db.session.flush()

        document = Document(
            source_id=source.id,
            project_id=project.id,
            original_name=original_name,
            storage_name=storage_name,
            file_type=extension.lstrip("."),
            content_hash=content_hash,
            extracted_text=extracted_text,
            uploaded_by=user_id,
            classification="internal",
            status="processed"
        )

        db.session.add(document)
        db.session.flush()

        for index, chunk_text in enumerate(chunks):
            db.session.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    text=chunk_text,
                    metadata_json={
                        "source_id": source.id,
                        "document_id": document.id,
                        "original_name": original_name,
                        "chunk_index": index
                    }
                )
            )

        db.session.add(
            AuditEvent(
                organisation_id=project.organisation_id,
                actor_id=user_id,
                action="document.uploaded",
                resource_type="document",
                resource_id=document.id
            )
        )

        db.session.commit()

        return jsonify({
            "message": "Document ingested successfully.",
            "source": {
                "id": source.id,
                "name": source.name,
                "type": source.source_type
            },
            "document": {
                "id": document.id,
                "filename": document.original_name,
                "file_type": document.file_type,
                "status": document.status,
                "extracted_characters": len(extracted_text),
                "chunks_created": len(chunks)
            }
        }), 201

    except Exception:
        db.session.rollback()

        if os.path.exists(storage_path):
            os.remove(storage_path)

        current_app.logger.exception("Document storage failed")
        return jsonify({"error": "Document could not be saved."}), 500


@ingestion_bp.get("/<project_id>/sources")
@jwt_required()
def list_sources(project_id):
    project, _, error = get_project_access(project_id)

    if error:
        return error

    sources = db.session.scalars(
        select(Source).where(
            Source.project_id == project.id
        ).order_by(Source.created_at.desc())
    ).all()

    return jsonify({
        "sources": [
            {
                "id": source.id,
                "name": source.name,
                "type": source.source_type,
                "created_at": source.created_at.isoformat()
            }
            for source in sources
        ],
        "count": len(sources)
    })
