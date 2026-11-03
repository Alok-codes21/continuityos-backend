
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.core import (
    Project,
    Membership,
    ProjectMember,
    Document,
    DocumentChunk,
    KnowledgeItem,
    AuditEvent,
)
from app.knowledge.extractor import extract_candidates
from app.models.core import ContinuityEvent


knowledge_bp = Blueprint(
    "knowledge",
    __name__,
    url_prefix="/api/projects",
)


def get_project_access(project_id, user_id):
    project = Project.query.filter_by(id=project_id).first()

    if not project:
        return None, None, None

    membership = Membership.query.filter_by(
        user_id=user_id,
        organisation_id=project.organisation_id,
    ).first()

    if not membership:
        return None, None, None

    project_member = ProjectMember.query.filter_by(
        project_id=project.id,
        user_id=user_id,
    ).first()

    is_manager = membership.role in ("admin", "manager")

    if not is_manager and not project_member:
        return None, None, None

    return project, membership, project_member


def can_review(membership, project_member):
    if membership.role in ("admin", "manager"):
        return True

    permissions = project_member.permissions or {} if project_member else {}
    return bool(permissions.get("can_manage_members"))


@knowledge_bp.post("/<project_id>/knowledge/extract")
@jwt_required()
def extract_project_knowledge(project_id):
    user_id = get_jwt_identity()

    project, membership, project_member = get_project_access(
        project_id, user_id
    )

    if not project:
        return jsonify({"error": "Project not found or access denied"}), 404

    if (
        membership.role not in ("admin", "manager")
        and not (project_member.permissions or {}).get("can_view_knowledge", False)
    ):
        return jsonify({"error": "Knowledge access denied"}), 403

    documents = Document.query.filter_by(project_id=project_id).all()

    created_count = 0
    skipped_count = 0

    for document in documents:
        chunks = DocumentChunk.query.filter_by(
            document_id=document.id
        ).all()

        for chunk in chunks:
            candidates = extract_candidates(chunk.text)

            for candidate in candidates:
                existing = KnowledgeItem.query.filter_by(
                    chunk_id=chunk.id,
                    item_type=candidate["item_type"],
                    title=candidate["title"],
                ).first()

                if existing:
                    skipped_count += 1
                    continue

                item = KnowledgeItem(
                    project_id=project_id,
                    document_id=document.id,
                    chunk_id=chunk.id,
                    item_type=candidate["item_type"],
                    title=candidate["title"],
                    description=candidate["description"],
                    evidence_text=candidate["evidence_text"],
                    evidence_location=candidate["evidence_location"],
                    extracted_by="rules-v1",
                    status="needs_review",
                    uncertainty="inferred",
                )

                db.session.add(item)
                created_count += 1

    db.session.add(AuditEvent(
        organisation_id=project.organisation_id,
        actor_id=user_id,
        action="knowledge.extraction",
        resource_type="project",
        resource_id=project_id,
    ))

    db.session.add(ContinuityEvent(
        project_id=project_id,
        actor_id=user_id,
        event_type="knowledge.extracted",
        entity_type="project",
        entity_id=project_id,
        summary=f"Knowledge extraction created {created_count} candidates",
        after_state={
            "created": created_count,
            "skipped_existing": skipped_count,
        },
    ))

    db.session.commit()

    return jsonify({
        "message": "Knowledge extraction completed",
        "created": created_count,
        "skipped_existing": skipped_count,
        "status": "needs_review",
    }), 200


@knowledge_bp.get("/<project_id>/knowledge")
@jwt_required()
def list_knowledge(project_id):
    user_id = get_jwt_identity()

    project, membership, project_member = get_project_access(
        project_id, user_id
    )

    if not project:
        return jsonify({"error": "Project not found or access denied"}), 404

    if (
        membership.role not in ("admin", "manager")
        and not (project_member.permissions or {}).get("can_view_knowledge", False)
    ):
        return jsonify({"error": "Knowledge access denied"}), 403

    query = KnowledgeItem.query.filter_by(project_id=project_id)

    item_type = request.args.get("type")
    status = request.args.get("status")
    uncertainty = request.args.get("uncertainty")

    if item_type:
        query = query.filter_by(item_type=item_type)

    if status:
        query = query.filter_by(status=status)

    if uncertainty:
        query = query.filter_by(uncertainty=uncertainty)

    items = query.order_by(KnowledgeItem.created_at.desc()).all()

    return jsonify({
        "items": [
            {
                "id": item.id,
                "type": item.item_type,
                "title": item.title,
                "description": item.description,
                "status": item.status,
                "uncertainty": item.uncertainty,
                "evidence": item.evidence_text,
                "evidence_location": item.evidence_location,
                "document_id": item.document_id,
                "extracted_by": item.extracted_by,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ],
        "total": len(items),
    }), 200


@knowledge_bp.post("/<project_id>/knowledge/<item_id>/review")
@jwt_required()
def review_knowledge(project_id, item_id):
    user_id = get_jwt_identity()

    project, membership, project_member = get_project_access(
        project_id, user_id
    )

    if not project:
        return jsonify({"error": "Project not found or access denied"}), 404

    if not can_review(membership, project_member):
        return jsonify({"error": "You cannot review knowledge items"}), 403

    item = KnowledgeItem.query.filter_by(
        id=item_id,
        project_id=project_id,
    ).first()

    if not item:
        return jsonify({"error": "Knowledge item not found"}), 404

    data = request.get_json(silent=True) or {}
    decision = data.get("decision")

    if decision not in ("approve", "reject"):
        return jsonify({
            "error": "decision must be 'approve' or 'reject'"
        }), 400

    previous_state = {
    "status": item.status,
    "uncertainty": item.uncertainty,
}

    item.status = "approved" if decision == "approve" else "rejected"
    item.uncertainty = "verified" if decision == "approve" else "inferred"
    item.reviewed_by = user_id
    item.reviewed_at = datetime.now(timezone.utc)

    db.session.add(ContinuityEvent(
        project_id=project_id,
        actor_id=user_id,
        event_type=f"knowledge.{decision}",
        entity_type="knowledge_item",
        entity_id=item.id,
        summary=f"Knowledge item '{item.title}' was {decision}d",
        before_state=previous_state,
        after_state={
            "status": item.status,
            "uncertainty": item.uncertainty,
        },
        evidence_document_id=item.document_id,
    ))

    db.session.add(AuditEvent(
        organisation_id=project.organisation_id,
        actor_id=user_id,
        action=f"knowledge.{decision}",
        resource_type="knowledge_item",
        resource_id=item.id,
    ))

    db.session.commit()

    return jsonify({
        "message": f"Knowledge item {item.status}",
        "id": item.id,
        "status": item.status,
        "uncertainty": item.uncertainty,
        "reviewed_by": user_id,
    }), 200
